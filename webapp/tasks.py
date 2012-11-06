#!/usr/bin/env python

from flask import Blueprint, request, jsonify, current_app

from db import api as api
from db import exceptions as exc
from webapp.errors import http_not_found

import webapp.utility as utility

tasks = Blueprint('tasks', __name__)


@tasks.route('/', methods=['GET', 'POST'])
def list_tasks():
    if request.method == 'POST':
        fields = api.task_get_columns()
        data = dict((field, request.json[field] if (field in request.json)
                     else None) for field in fields)

        task = api.task_create(data)
        if 'node_id' in task:
            task_semaphore = 'task-for-%s' % task['node_id']
            current_app.logger.debug('notifying event %s' % task_semaphore)
            utility.notify(task_semaphore)

        href = request.base_url + str(task['id'])
        msg = {'status': 201,
               'message': 'Task Created',
               'task': task,
               'ref': href}
        resp = jsonify(msg)
        resp.status_code = 201
        resp.headers['Location'] = href
    else:
        tasks = api.tasks_get_all()
        resp = jsonify({'tasks': tasks})
    return resp


@tasks.route('/<task_id>', methods=['GET', 'PUT', 'DELETE'])
def task_by_id(task_id):
    if request.method == 'PUT':
        fields = api.task_get_columns()
        data = dict((field, request.json[field]) for field in fields
                    if field in request.json)
        task = api.task_update_by_id(task_id, data)

        if 'node_id' in task:
            task_semaphore = 'task-for-%s' % task['node_id']
            current_app.logger.debug('notifying event %s' % task_semaphore)
            utility.notify(task_semaphore)

        resp = jsonify({'task': task})
        return resp
    elif request.method == 'DELETE':
        try:
            if api.task_delete_by_id(task_id):
                msg = {'status': 200, 'message': 'Task deleted'}
                resp = jsonify(msg)
                resp.status_code = 200
                return resp
        except exc.NodeNotFound:
            return http_not_found()
    else:
        task = api.task_get_by_id(task_id)
        if not task:
            return http_not_found()
        else:
            resp = jsonify({'task': task})
            return resp
