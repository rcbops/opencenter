#!/usr/bin/env python

import json
from time import time

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app

from db import api as api
from db import exceptions as exc
from db.database import db_session
from webapp.errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_not_implemented)

import webapp.utility as utility
from ast import AstBuilder, FilterTokenizer

filters = Blueprint('filters', __name__)
object_type = 'filters'
singular_object_type = 'filter'


@filters.route('/', methods=['GET', 'POST'])
def list():
    if request.method == 'POST':
        fields = api._model_get_columns(object_type)

        data = dict((field, request.json[field] if (field in request.json)
                     else None) for field in fields)

        model_object = api._model_create(object_type, data)

        href = request.base_url + str(model_object['id'])
        msg = {'status': 201,
               'message': '%s Created' % singular_object_type.capitalize(),
               '%s' % singular_object_type: model_object,
               'ref': href}
        resp = jsonify(msg)
        resp.status_code = 201
        resp.headers['Location'] = href
    else:
        model_objects = api._model_get_all(object_type)
        resp = jsonify({object_type: model_objects})
    return resp


@filters.route('/filter', methods=['POST'])
def filter():
    builder = AstBuilder(FilterTokenizer(),
                         '%s: %s' % (object_type, request.json['filter']))
    return jsonify({object_type: builder.eval()})


@filters.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def object_by_id(object_id):
    if request.method == 'PUT':
        fields = api._model_get_columns(object_type)
        data = dict((field, request.json[field]) for field in fields
                    if field in request.json)
        model_object = api._model_update_by_id(object_type, object_id, data)
        resp = jsonify({singular_object_type: model_object})
        return resp
    elif request.method == 'DELETE':
        try:
            if api._model_delete_by_id(object_id):
                msg = {'status': 200,
                       'message': '%s deleted' % (singular_object_type, )}
                resp = jsonify(msg)
                resp.status_code = 200
                return resp
        except exc.NodeNotFound, e:
            return http_not_found()
    else:
        model_object = api._model_get_by_id(object_type, object_id)
        if not model_object:
            return http_not_found()
        else:
            resp = jsonify({singular_object_type: model_object})
            return resp
