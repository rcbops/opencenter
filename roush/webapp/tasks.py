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

@bp.route('/<object_id>/logs', methods=['GET'])
def task_log(task_id):
    try:
        task = api._model_get_by_id('tasks', task_id)
    except exceptions.IdNotFound:
        return http_response(404, 'not found')

    node_id = task['node_id']

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('',0))
    s.listen(1)

    family, socktype, proto, canonname, sockaddr = s.getsockname()

    conn, addr = s.accept()
    data = conn.recv(1024)

    conn.close()
    s.shutdown(2)
    s.close()

    return http_response(200, log=data)
