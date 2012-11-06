#!/usr/bin/env python

import flask
from webapp import generic
from webapp import utility

object_type = 'tasks'
bp = flask.Blueprint(object_type, __name__)


@bp.route('/', methods=['GET', 'POST'])
def list():
    result = generic.list(object_type)

    if flask.request.method == 'POST':
        data = flask.request.json
        if 'node_id' in data:
            task_semaphore = 'task-for-%s' % data['node_id']
            flask.current_app.logger.debug('notifying event %s' % task_semaphore)
            utility.notify(task_semaphore)

    return result


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def task_by_id(object_id):
    result = generic.object_by_id(object_type, object_id)

    if flask.request.method == 'PUT':
        task = flask.request.json
        if 'node_id' in task:
            flask.current_app.logger.debug('Task: %s' % task)
            task_semaphore = 'task-for-%s' % task['node_id']
            flask.current_app.logger.debug('notifying event %s' % task_semaphore)
            utility.notify(task_semaphore)

    return result
