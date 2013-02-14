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

import time

import flask

from roush.db import exceptions
from roush.db.api import api_from_models
from roush.webapp.auth import requires_auth
from roush.webapp import utility


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

    # TODO: Generalize the block of code with a TODO below here.
#    if updated_object is not None and object_type in related_notifications:
#        for field, entity in related_notifications[object_type].iteritems():
#            if field in updated_object and updated_object[field] is not None:
#                semaphore = '%s-id-%s' % (entity, updated_object[field])
#                utility.notify(semaphore)

    # TODO (wilk or rpedde): Use specific notifications for inheritance
    node_id = None
    if object_type == 'facts':
        node_id = updated_object['node_id']
    if object_type == 'nodes':
        node_id = updated_object['id']
    if node_id is not None:
        api = api_from_models()
        node_id = int(node_id)
        # We're just going to notify every child when containers are updated
        try:
            node = api._model_get_by_id('nodes', node_id)
        except exceptions.IdNotFound:
            return

        if node is not None and 'container' in node['facts'].get(
                'backends', []):
            children = utility.get_direct_children(node_id, api)
            for child in children:
                semaphore = 'nodes-id-%s' % child['id']
                utility.notify(semaphore)
        # Update transaction for node and children
        id_list = utility.fully_expand_nodelist([node_id], api)
        # TODO(shep): this needs to be better abstracted
        _update_transaction_id('nodes', id_list)
    # Need a codepath to update transaction for attr modifications
    if object_type == "attrs":
        node_id = updated_object['node_id']
        # TODO(shep): this needs to be better abstracted
        _update_transaction_id('nodes', [node_id])


def _update_transaction_id(object_model, id_list=None):
    """
    Updates the in-memory transaction dict when object_models are updated.

    Arguments:
    id_list -- A list of <object_model>_ids

    Returns:
    None
    """
    if id_list is not None:
        trans = flask.current_app.transactions[object_model]
        trans_time = time.time()
        lock_name = '%s-txid' % object_model

        utility.lock_acquire(lock_name)

        try:
            while trans_time in trans:
                trans_time += 0.000001

            trans[trans_time] = set(id_list)
        except:
            utility.lock_release(lock_name)
            raise

        utility.lock_release(lock_name)

        # prune any updates > 5 min ago
        trans_time_past = trans_time - (60 * 5)
        for k in [x for x in trans.keys() if x < trans_time_past]:
            del trans[k]

        semaphore_name = '%s-changes' % object_model
        utility.notify(semaphore_name)


@requires_auth()
def list(object_type):
    s_obj = singularize(object_type)

    api = api_from_models()
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


@requires_auth()
def object_by_id(object_type, object_id):
    s_obj = singularize(object_type)

    api = api_from_models()
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

        try:
            model_object = api._model_get_by_id(object_type, object_id)
        except exceptions.IdNotFound:
            return http_response(404, 'not found')

        return http_response(200, 'success', **{s_obj: model_object})
    else:
        return http_notfound(msg='Unknown method %s' % flask.request.method)


@requires_auth()
def http_solver_request(node_id, constraints,
                        api=None, result=None, plan=None):
    if api is None:
        api = api_from_models()
    try:
        task, solution_plan = utility.solve_and_run(node_id,
                                                    constraints,
                                                    api=api,
                                                    plan=plan)
    except ValueError as e:
        # no adventurator, or the generated ast was broken somehow
        return http_response(403, msg=str(e))

    if task is None:
        is_solvable, requires_input, solution_plan = utility.solve_for_node(
            node_id, constraints, api, plan=plan)

        if ((not is_solvable) and requires_input):
            return http_response(409, msg='need additional input',
                                 plan=solution_plan)
        if not is_solvable:
            return http_response(403, msg='cannot be solved',
                                 friendly='sorry about that')

    # here we need to return the object (node/fact),
    # but should consequence be applied?!?
    # no, we are just going to return a bare 20x
    if result is None:
        result = {}

    result['plan'] = solution_plan
    result['task'] = task

    return http_response(202, 'executing change', **result)
