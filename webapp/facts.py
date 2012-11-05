#!/usr/bin/env python

import generic


from flask import Blueprint, Response, request, jsonify, url_for

from db import api

object_type = 'facts'
singular_object_type = generic.singularize(object_type)

bp = Blueprint(object_type, __name__)


@bp.route('/', methods=['GET'])
def list():
    return generic.list(object_type)


@bp.route('/', methods=['POST'])
def create():
    old_fact = None

    # if we are creating with the same host_id and key, then we'll just update
    fields = api._model_get_columns(object_type)
    data = dict((field, request.json[field] if (field in request.json)
                 else None) for field in fields)

    model_object = None
    resp = None

    if 'node_id' in data and 'key' in data:
        old_fact = api._model_get_first_by_filter(object_type,
                                                  {'node_id': data['node_id'],
                                                   'key': data['key']})

    if old_fact:
        model_object = api._model_update_by_id(
            object_type, old_fact['id'], data)
    else:
        model_object = api._model_create(object_type, data)

    href = request.base_url + str(model_object['id'])
    msg = {'status': 201,
           'message': '%s Created' % singular_object_type.capitalize(),
           '%s' % singular_object_type: model_object,
           'ref': href}

    resp = jsonify(msg)
    resp.status_code = 201
    resp.headers['Location'] = href

    return resp


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)
