#!/usr/bin/env python

import json
from pprint import pprint
from time import time

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from db import api as api
from db import exceptions as exc
from db.database import db_session
from db.models import Nodes, Roles, Clusters, Tasks
from errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_not_implemented)

from filters import AstBuilder, FilterTokenizer

tasks = Blueprint('tasks', __name__)


@tasks.route('/', methods=['GET', 'POST'])
def list_tasks():
    if request.method == 'POST':
        # TODO(shep): sanity check action and payload
        fields = {'node_id': None,
                  'action': None,
                  'payload': 'json',
                  'state': 'pending',
                  'result': 'json',
                  'completed': None,
                  'expires': None}

        for k, v in fields.iteritems():
            if k in request.json:
                fields[k] = request.json[k]
            else:
                fields[k] = None

        task = Tasks(node_id=fields['node_id'], action=fields['action'],
                     payload=fields['payload'], state=fields['state'],
                     result=fields['result'], submitted=int(time()),
                     completed=fields['completed'], expires=fields['expires'])
        db_session.add(task)
        msg = {'status': 500, 'message': 'Internal Error'}
        try:
            db_session.commit()
            # FIXME(shep): add a ref
            href = request.base_url + str(task.id)
            msg = {'status': 201, 'message': 'Task Created',
                   'ref': href,
                   'task': dict((c, getattr(task, c))
                                for c in task.__table__.columns.keys())}
        except IntegrityError, e:
            db_session.rollback()
            return http_conflict(e)

        resp = jsonify(msg)
        resp.status_code = 201
        resp.headers['Location'] = href
    else:
        tasks = api.tasks_get_all()
        resp = jsonify({'tasks': tasks})
    return resp


@tasks.route('/filter', methods=['POST'])
def filter_tasks():
    builder = AstBuilder(FilterTokenizer(),
                         'tasks: %s' % request.json['filter'])
    return jsonify({'tasks': builder.eval()})


@tasks.route('/<task_id>', methods=['GET', 'PUT'])
def task_by_id(task_id):
    if request.method == 'PUT':
        fields = api.task_get_columns()
        data = dict((field, request.json[field]) for field in fields
                    if field in request.json)
        task = api.task_update_by_id(task_id, data)
        resp = jsonify({'task': task})
        return resp
    else:
        task = api.task_get_by_id(task_id)
        if not task:
            return http_not_found()
        else:
            resp = jsonify({'task': task})
            return resp
