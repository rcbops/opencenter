#!/usr/bin/env python

import flask

import utility
from roush.db import exceptions
from roush.db.api import api_from_models


api = api_from_models()


# Some notifications are related... facts updates must fire associated
# node, for example.  This keeps those relationships.  There might be
# others in the future, though.
related_notifications = {
    "facts": {"node_id": "nodes"}
}


def singularize(what):
    return what[:-1]


def http_response(result=200, msg='did the needful', **kwargs):
    resp = {'status': result,
            'message': msg}

    resp.update(kwargs)

    jsonified_response = flask.jsonify(resp)
    jsonified_response.status_code = result

    if 'ref' in kwargs:
        jsonified_response.headers['Location'] = kwargs['ref']

    return jsonified_response


def http_notfound(result=404, msg=None, **kwargs):
    if msg is None:
        msg = 'Not Found: %s' % flask.request.url

    return http_response(result, msg, **kwargs)


def http_notimplemented(result=501, msg=None, **kwargs):
    if msg is None:
        msg = 'Not Implemented'
    return http_response(result, msg, **kwargs)


def http_badrequest(result=400, msg=None, **kwargs):
    if msg is None:
        msg = 'Bad Request'
    return http_response(result, msg, **kwargs)


def http_conflict(result=409, msg=None, **kwargs):
    if msg is None:
        msg = 'Conflict'
    return http_response(result, msg, **kwargs)


def _notify(updated_object, object_type, object_id):
    semaphore = '%s-id-%s' % (object_type, object_id)
    utility.notify(semaphore)

    if updated_object is not None and object_type in related_notifications:
        for field, entity in related_notifications[object_type].iteritems():
            if field in updated_object and updated_object[field] is not None:
                semaphore = '%s-id-%s' % (entity, updated_object[field])
                utility.notify(semaphore)


def list(object_type):
    s_obj = singularize(object_type)

    if flask.request.method == 'POST':
        data = flask.request.json

        try:
            model_object = api._model_create(object_type, data)
        except KeyError as e:
            # missing required field
            return http_badrequest(msg=str(e))

        _notify(model_object, object_type, model_object['id'])
        href = flask.request.base_url + str(model_object['id'])

        return http_response(201, '%s Created' % s_obj.capitalize(),
                             ref=href, **{s_obj: model_object})
    elif flask.request.method == 'GET':
        model_objects = api._model_get_all(object_type)
        return http_response(200, 'success', **{object_type: model_objects})
    else:
        return http_notfound(msg='Unknown method %s' % flask.request.method)


def object_by_id(object_type, object_id):
    s_obj = singularize(object_type)

    if flask.request.method == 'PUT':
        # we just updated something, poke any waiters
        model_object = api._model_update_by_id(object_type, object_id,
                                               flask.request.json)

        _notify(model_object, object_type, object_id)

        return http_response(200, '%s Updated' % s_obj.capitalize(),
                             **{s_obj: model_object})
    elif flask.request.method == 'DELETE':
        try:
            if api._model_delete_by_id(object_type, object_id):
                return http_response(200, '%s deleted' % s_obj.capitalize())
            _notify(None, object_type, object_id)
        except exceptions.IdNotFound:
            return http_response(404, 'not found')
    elif flask.request.method == 'GET':
        if 'poll' in flask.request.args:
            # we're polling
            semaphore = '%s-id-%s' % (object_type, object_id)
            utility.wait(semaphore)

        model_object = api._model_get_by_id(object_type, object_id)

        if not model_object:
            return http_response(404, 'not found')
        else:
            return http_response(200, 'success', **{s_obj: model_object})
    else:
        return http_notfound(msg='Unknown method %s' % flask.request.method)
