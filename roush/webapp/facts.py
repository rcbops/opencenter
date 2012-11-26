#!/usr/bin/env python

import generic
import flask

from roush.db import api

object_type = 'facts'
singular_object_type = generic.singularize(object_type)

bp = flask.Blueprint(object_type, __name__)


@bp.route('/', methods=['GET'])
def list():
    return generic.list(object_type)


@bp.route('/', methods=['POST'])
def create():
    old_fact = None

    # if we are creating with the same host_id and key, then we'll just update
    # fields = api._model_get_columns(object_type)

    data = flask.request.json

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
        try:
            model_object = api._model_create(object_type, data)
        except KeyError as e:
            # missing required field
            return generic.http_badrequest(msg=str(e))

    href = flask.request.base_url + str(model_object['id'])
    return generic.http_response(201, '%s Created' %
                                 singular_object_type.capitalize(), ref=href,
                                 **{singular_object_type: model_object})


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)
