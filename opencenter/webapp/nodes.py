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

import time
import socket

import flask

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
    except exceptions.NodeNotFound:
        message = 'Node %s not found.' % args['node_id']
        return generic.http_notfound(msg=message)
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


@bp.route('/whoami', methods=['POST'])
def whoami():
    api = api_from_models()
    body = flask.request.json
    if body is None or (not 'hostname' in body):
        return generic.http_badrequest(
            msg="'hostname' not found in json object")
    hostname = body['hostname']
    nodes = api._model_query(
        'nodes',
        'name = "%s"' % hostname)
    node = None
    if len(nodes) == 0:
        # register a new node
        node = api._model_create('nodes', {'name': hostname})
        api._model_create('facts',
                          {'node_id': node['id'],
                           'key': 'backends',
                           'value': ['node', 'agent']})
        api._model_create('attrs',
                          {'node_id': node['id'],
                           'key': 'converged',
                           'value': True})

        if hostname == socket.gethostname():
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
        node = api._model_get_by_id('nodes', node['id'])
    else:
        node = nodes[0]
    return generic.http_response(200, 'success',
                                 **{'node': node})
