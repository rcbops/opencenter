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

import flask
import socket
import netifaces

from roush.db import exceptions
from roush.db.api import api_from_models
from roush.webapp import generic
from roush.webapp import utility

api = api_from_models()
object_type = 'tasks'
bp = flask.Blueprint(object_type, __name__)


@bp.route('/', methods=['GET', 'POST'])
def list():
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
    try:
        task = api._model_get_by_id('tasks', task_id)
    except exceptions.IdNotFound:
        return generic.http_response(404, 'not found')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    s.listen(1)

    addr, port = s.getsockname()
    if addr == '0.0.0.0':
        # we need something more specific.  This is
        # pretty naive, but works.  If we could get the
        # flask fd, we could getsockname on that side
        # and see what we requested on.  that would
        # likely be a better guess.
        interface_list = netifaces.interfaces()
        iface = 'eth0'
        if not iface in interface_list:
            iface = 'en0'

        try:
            addr = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']
        except Exception:
            # we don't have an eth0, or ipv4 or something else.  Enough that
            # we aren't going to come up with a simple way to do this, so
            # we'll punt
            #
            # randomly find an ip address that isn't loopback...
            addr_list = []

            addr = None

            for iface in interface_list:
                if netifaces.AF_INET in netifaces.ifaddresses(iface):
                    someaddrs = netifaces.ifaddresses(iface)[netifaces.AF_INET]
                    for paddr in someaddrs:
                        if 'addr' in paddr:
                            addr_list.append(paddr['addr'])

            for paddr in addr_list:
                if not paddr.startswith('127'):
                    addr = paddr

            if not addr:
                s.close()
                return generic.http_response(500, 'cannot determine bind')

    new_task = api._model_create('tasks', {'node_id': task['node_id'],
                                           'action': 'logfile.tail',
                                           'payload': {'task_id': task['id'],
                                                       'dest_ip': addr,
                                                       'dest_port': port}})

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
        s.close()
        api._model_update('tasks', new_task['id'],
                          {'state': 'cancelled'})

        return generic.http_response(404, 'cannot fetch logs')

    data = conn.recv(1024)

    conn.close()
    s.close()

    return generic.http_response(200, log=data)
