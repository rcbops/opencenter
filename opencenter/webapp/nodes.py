#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

import flask
import logging
import time

from opencenter.db import exceptions
from opencenter.db.api import api_from_models
from opencenter.webapp import ast
# from opencenter.webapp import auth
from opencenter.webapp import generic
from opencenter.webapp import utility
from opencenter.webapp.utility import unprovisioned_container


object_type = 'nodes'
bp = flask.Blueprint(object_type,  __name__)


@bp.route('/', methods=['GET', 'POST'])
def root():
    return generic.list(object_type)


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)


@bp.route('/<node_id>/tasks_blocking', methods=['GET'])
def tasks_blocking_by_node_id(node_id):
    api = api_from_models()

    # README(shep): Using last_checkin attr for agent-health
    timestamp = int(time.time())
    args = {'node_id': node_id, 'key': 'last_checkin', 'value': timestamp}
    try:
        r = api.attr_create(args)
    except exceptions.IdNotFound:
        message = 'Node %s not found.' % args['node_id']
        return generic.http_notfound(msg=message)
    except exceptions.IdInvalid:
        return generic.http_badrequest()
    #DB does not hit updater, so we need to notify
    generic._update_transaction_id('nodes', id_list=[node_id])
    generic._update_transaction_id('attrs', id_list=[r['id']])

    while True:
        task = api.task_get_first_by_query("node_id=%d and state='pending'" %
                                           int(node_id))
        if task is None:
            semaphore = 'task-for-%s' % node_id
            flask.current_app.logger.debug('waiting on %s' % semaphore)
            if not utility.wait(semaphore):
                flask.current_app.logger.error("ERROR ON WAIT")
                # utility.clear(semaphore)
                return generic.http_notfound(msg='no task found')
            else:
                flask.current_app.logger.error("SUCCESS ON WAIT")
        else:
            # utility.clear(semaphore)
            return generic.http_response(task=task)

    #         utility.wait(semaphore)

    # task = api.task_get_first_by_query("node_id=%d and state='pending'" %
    #                                    int(node_id))
    # if task:
    #     utility.clear(semaphore)
    #     result = flask.jsonify({'task': task})
    # else:
    #     result = generic.http_notfound(msg='no task found')
    # return result


@bp.route('/<node_id>/tasks', methods=['GET'])
def tasks_by_node_id(node_id):
    api = api_from_models()
    # Display only tasks with state=pending
    task = api.task_get_first_by_query("node_id=%d and state='pending'" %
                                       int(node_id))
    if not task:
        return generic.http_notfound()
    else:
        resp = generic.http_response(task=task)
        task['state'] = 'delivered'
        api._model_update_by_id('tasks', task['id'], task)
        return resp


@bp.route('/<node_id>/adventures', methods=['GET'])
def adventures_by_node_id(node_id):
    api = api_from_models()
    node = api.node_get_by_id(node_id)
    if not node:
        return generic.http_notfound()
    else:
        all_adventures = api.adventures_get_all()
        available_adventures = []
        for adventure in all_adventures:
            builder = ast.FilterBuilder(ast.FilterTokenizer(),
                                        adventure['criteria'],
                                        api=api)
            try:
                root_node = builder.build()
                if root_node.eval_node(node, builder.functions):
                    available_adventures.append(adventure)
            except Exception as e:
                flask.current_app.logger.warn(
                    'adv err %s: %s' % (adventure['name'], str(e)))

        # adventures = api.adventures_get_by_node_id(node_id)
        resp = flask.jsonify({'adventures': available_adventures})
    return resp


def _whoami_backwards_compatibility(api, hostname):
    '''Associate existing node with new whoami registration.'''
    query = 'name = "%s" and "registered" !in attrs' % hostname
    node = api.node_get_first_by_query(query)
    if node is None:
        return
    api._model_create('attrs',
                      {'node_id': node['id'],
                       'key': 'registered',
                       'value': True})
    return node


@bp.route('/whoami', methods=['POST'])
def whoami():
    log = logging.getLogger('.'.join((__name__, 'whoami')))
    log.info('Request received.')
    api = api_from_models()
    body = flask.request.json
    message = 'Node ID or hostname required.'
    try:
        #if id not supplied assume it is a new agent
        node_id = body['node_id']
    except TypeError:
        return generic.http_badrequest(msg=message)
    except KeyError:
        try:
            hostname = body['hostname']
        except KeyError:
            return generic.http_badrequest(msg=message)
        else:
            node = _whoami_backwards_compatibility(api, hostname)
            if node is None:
                node = api._model_create('nodes', {'name': hostname})
                api._model_create('facts',
                                  {'node_id': node['id'],
                                   'key': 'backends',
                                   'value': ['node', 'agent']})
                api._model_create('attrs',
                                  {'node_id': node['id'],
                                   'key': 'converged',
                                   'value': True})
                api._model_create('attrs',
                                  {'node_id': node['id'],
                                   'key': 'registered',
                                   'value': False})
            return generic.http_response(200, 'Node ID assigned.',
                                         node_id=node['id'])
    log.info('Node id %s received.' % node_id)
    try:
        node = api._model_get_by_id('nodes', node_id)
    except exceptions.IdNotFound:
        message = 'Node %s not found.' % node_id
        return generic.http_notfound(msg=message)
    except exceptions.IdInvalid:
        return generic.http_badrequest('Node ID must be an integer.')

    if not node['attrs']['registered']:
        # register a new node
        log.info('Registering %s' % node_id)
        try:
            hostidfile = flask.current_app.config['hostidfile']
        except KeyError:
            log.error('hostidfile not set in config.')
            return generic.http_response(500, 'hostidfile not set on server.')
        reg_file = '.'.join((hostidfile, 'registering'))
        try:
            with open(reg_file) as f:
                server_id = f.read().strip()
        except IOError:
            log.error('Unable to read server ID from %s.' % reg_file)
            server_id = None
        try:
            server_node = api._model_get_by_id('nodes', server_id)
        except (exceptions.IdInvalid, exceptions.IdNotFound):
            #log this as an error and assume agent not on server
            log.error('Server ID from in %s is invalid.' % reg_file)
            server_node = {'id': None}
        if server_node['id'] == node['id']:
            api._model_create('facts',
                              {'node_id': node['id'],
                               'key': 'parent_id',
                               'value': 3})
            api._model_create('attrs',
                              {'node_id': node['id'],
                              'key': 'server-agent',
                              'value': True})
        else:
            unprovisioned_id = unprovisioned_container()['id']
            api._model_create('facts',
                              {'node_id': node['id'],
                               'key': 'parent_id',
                               'value': unprovisioned_id})
        #update registered attr to True
        attr_query = "node_id=%d and key='registered'" % node['id']
        reg_attr = api.attr_get_first_by_query(attr_query)
        reg_attr['value'] = True
        api._model_update_by_id('attrs', reg_attr['id'], reg_attr)
        node = api._model_get_by_id('nodes', node['id'])
        log.info('Registration complete for %s' % node_id)
    return generic.http_response(200, 'success', **{'node': node})
