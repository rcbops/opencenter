#!/usr/bin/env python

from flask import request, jsonify

from db import api as api
import db.exceptions as exc


def singularize(what):
    return what[:-1]


def http_response(result=200, msg='did the needful', **kwargs):
    resp = {'status': result,
            'message': msg}

    resp.update(kwargs)

    jsonified_response = jsonify(resp)
    jsonified_response.status_code = result
    return jsonified_response


def list(object_type):
    s_obj = singularize(object_type)

    if request.method == 'POST':
        fields = api._model_get_columns(object_type)

        data = dict((field, request.json[field] if (field in request.json)
                     else None) for field in fields)

        model_object = api._model_create(object_type, data)

        href = request.base_url + str(model_object['id'])

        return http_response(201, '%s Created' % s_obj.capitalize(),
                             ref=href, **{s_obj: model_object})
    else:
        model_objects = api._model_get_all(object_type)
        return http_response(200, 'success', **{object_type: model_objects})


def object_by_id(object_type, object_id):
    s_obj = singularize(object_type)

    if request.method == 'PUT':
        model_object = api._model_update_by_id(object_type, object_id,
                                               request.json)
        return http_response({s_obj: model_object})
    elif request.method == 'DELETE':
        try:
            if api._model_delete_by_id(object_type, object_id):
                return http_response(200, '%s deleted' % s_obj.capitalize())
        except exc.IdNotFound:
            return http_response(404, 'not found')
    else:
        model_object = api._model_get_by_id(object_type, object_id)
        if not model_object:
            return http_response(404, 'not found')
        else:
            return http_response(200, 'success', **{s_obj: model_object})
