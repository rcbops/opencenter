#!/usr/bin/env python

import flask
import generic
import utility

from roush.db.api import api_from_models


api = api_from_models()
object_type = 'adventures'
bp = flask.Blueprint(object_type, __name__)


@bp.route('/', methods=['GET', 'POST'])
def list():
    return generic.list(object_type)


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)


@bp.route('/<adventure_id>/execute', methods=['POST'])
def execute_adventure(adventure_id):
    data = flask.request.json

    if not 'nodes' in data:
        return generic.http_badrequest(msg='no nodes specified')

    try:
        task = utility.run_adventure(adventure_id=adventure_id,
                                     nodes=data['nodes'])
    except ValueError as e:
        return generic.http_badrequest(msg=str(e))

    href = flask.request.base_url + str(task['id'])

    return generic.http_response(201, 'Task Created', task=task,
                                 ref=href)
