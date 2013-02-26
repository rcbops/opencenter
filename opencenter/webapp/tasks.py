#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import gevent
import logging
import socket
import time
import uuid

import flask
import netifaces

from opencenter.db import exceptions
from opencenter.db.api import api_from_models
from opencenter.webapp import generic
from opencenter.webapp import utility

object_type = 'tasks'
bp = flask.Blueprint(object_type, __name__)
watched_tasks = {}
task_last_run = 0


def _clean_tasks():
    """
    clean up completed tasks over task_reaping_threshold seconds old.
    This is set in the [main] section of the config.  The default is
    300 seconds (5 min).

    This will not run more often than once per minute.
    """

    current_time = time.time()
    if current_time < task_last_run + 60:
        return

    api = api_from_models()

    reaping_threshold = flask.current_app.config['task_reaping_threshold']
    expiration_threshold = current_time - reaping_threshold

    expired_tasks = api._model_query(
        object_type,
        '(state = "done" or state="cancelled") '
        'and completed < %d' %
        expiration_threshold)

    for task in expired_tasks:
        api._model_delete_by_id(object_type, task['id'])


@bp.route('/', methods=['GET', 'POST'])
def list():
    _clean_tasks()

    result = generic.list(object_type)

    if flask.request.method == 'POST':
        data = flask.request.json
        if 'node_id' in data:
            task_semaphore = 'task-for-%s' % data['node_id']
            flask.current_app.logger.debug('notifying event %s' %
                                           task_semaphore)
            utility.notify(task_semaphore)

    return result


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def task_by_id(object_id):
    result = generic.object_by_id(object_type, object_id)

    if flask.request.method == 'PUT':
        api = api_from_models()
        task = api.task_get_by_id(object_id)
        if 'node_id' in task:
            flask.current_app.logger.debug('Task: %s' % task)
            task_semaphore = 'task-for-%s' % task['node_id']
            flask.current_app.logger.debug('notifying event %s' %
                                           task_semaphore)
            utility.notify(task_semaphore)

    return result


@bp.route('/<task_id>/logs', methods=['GET'])
def task_log(task_id):
    """
    Tail a logfile on a client.  Given a task id, this asks
    the client that ran it grab the last 1k of the logs from
    that task and push them at the server on an ephemeral port.

    This gets returned as 'log' in the return json blob.
    """

    api = api_from_models()
    try:
        task = api._model_get_by_id('tasks', task_id)
    except exceptions.IdNotFound:
        return generic.http_notfound(msg='Task %s not found' % task_id)

    watching = flask.request.args.get('watch', False) is not False

    s = gevent.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    s.listen(1)

    addr, port = s.getsockname()
    if addr == '0.0.0.0':
        # we need something more specific.  This is
        # pretty naive, but works.  If we could get the
        # flask fd, we could getsockname on that side
        # and see what we requested on.  that would
        # likely be a better guess.

        # generate a list of all interfaces with
        # non-loopback ipv4 addresses.
        addr = None

        addrs = {}
        for iface in netifaces.interfaces():
            if netifaces.AF_INET in netifaces.ifaddresses(iface):
                for ablock in netifaces.ifaddresses(iface)[netifaces.AF_INET]:
                    if not iface in addrs:
                        addrs[iface] = []
                    if not ablock['addr'].startswith('127'):
                        addrs[iface].append(ablock['addr'])

                if iface in addrs and len(addrs[iface]) == 0:
                    addrs.pop(iface)

        if len(addrs) == 0:
            s.close()
            return generic.http_response(400, 'cannot determine interface')

        # try least-to-most interesting
        for iface in ['en1', 'en0', 'eth1', 'eth0']:
            if iface in addrs:
                addr = addrs[iface][0]

        # just grab the first
        if not addr:
            addr = addrs[addrs.keys().pop(0)][0]

    client_action = 'logfile.watch' if watching else 'logfile.tail'

    payload = {'node_id': task['node_id'],
               'action': client_action,
               'payload': {'task_id': task['id'],
                           'dest_ip': addr,
                           'dest_port': port}}
    if watching:
        payload['payload']['timeout'] = 30

    new_task = api._model_create('tasks', payload)

    # this should really be done by the data model.  <sigh>
    task_semaphore = 'task-for-%s' % task['node_id']
    flask.current_app.logger.debug('notifying event %s' %
                                   task_semaphore)
    utility.notify(task_semaphore)

    # force the wake
    utility.sleep(0.1)

    # now wait for a few seconds to see if we get the
    # connection
    s.settimeout(10)

    try:
        conn, addr = s.accept()
    except socket.timeout:
        flask.current_app.logger.error('Error waiting for '
                                       'client connect on log tail')

        s.close()
        api._model_update_by_id('tasks', new_task['id'],
                                {'state': 'cancelled'})

        return generic.http_notfound(msg='cannot fetch logs')

    if watching:
        watch = str(uuid.uuid1())
        watched_tasks[watch] = {
            'socket': conn,
            'time': time.time(),
            'task_id': new_task['id'],
            'notifier': gevent.event.Event(),
            'accept_socket': s,
            'event': gevent.spawn(
                lambda: _serve_connection(
                    api, watch))}

        return generic.http_response(200, request=watch)

    # otherwise, just tail
    data = conn.recv(1024)

    conn.close()
    s.close()

    return generic.http_response(200, log=data)


@bp.route('/<task_id>/logs/<transaction>', methods=['GET'])
def task_log_tail(task_id, transaction):
    if not transaction in watched_tasks:
        flask.current_app.logger.error(
            '%s not in watched tasks: %s' % (transaction,
                                             watched_tasks))

        return generic.http_notfound()

    watched_tasks[transaction]['notifier'].set()

    # yield to greenlets
    gevent.sleep(0)

    if not 'generator' in watched_tasks[transaction]:
        # something very wrong here
        flask.current_app.logger.error(
            'no generator in %s: %s' % (
                transaction,
                watched_tasks[transaction]))

        watched_tasks.pop(transaction)
        return generic.http_notfound()

    return flask.Response(watched_tasks[transaction]['generator'],
                          mimetype='text/plain')


def _serve_connection(api, watch):
    logger = logging.getLogger('opencenter.webapp.tasks')

    watch_info = watched_tasks[watch]

    listen_socket = watch_info['socket']
    accept_socket = watch_info['accept_socket']

    logger.debug('Waiting for wakeup')

    # we'll wait for the follow-up request
    if watch_info['notifier'].wait(30):
        # we've been woken up -- someone is
        # asking for the file.  We should have
        # a response now.
        def generate(watch, sock_in, accept_socket):
            sock_in.settimeout(30)

            while True:
                data = sock_in.recv(1024)
                if data == '':
                    # remote disconnected
                    return
                yield data

            sock_in.close()
            accept_socket.close()

            try:
                watched_tasks.pop(watch)
            except KeyError:
                pass

        logger.debug('Woke up -- spinning generator')
        wrapped_socket = gevent.socket.fromfd(listen_socket.fileno(),
                                              socket.AF_INET,
                                              socket.SOCK_STREAM)
        watch_info['generator'] = generate(watch, wrapped_socket,
                                           accept_socket)

        # we'll wait 30 seconds for the other side to pick it up...
        # if it doesn't, we'll just throw away the transaction.
        gevent.sleep(30)
    else:
        logger.debug('Error waking up.  Destroying all the things')

    try:
        watched_tasks.pop(watch)
    except KeyError:
        # popped on the other side.  this is okay
        pass
