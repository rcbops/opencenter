#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

import time

import flask
import gevent

from opencenter.db import exceptions
from opencenter.db.api import api_from_models
from opencenter.webapp.auth import requires_auth
from opencenter.webapp import utility


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
    if object_type not in ('attrs', 'facts', 'nodes'):
        return
    try:
        node_id = updated_object['node_id']
        node = None
    except KeyError:
        node_id = updated_object['id']
        node = updated_object
    if object_type != "attrs":
        api = api_from_models()
        # We're just going to notify every child when containers are updated
        if node is None:
            try:
                node = api._model_get_by_id('nodes', node_id)
            except (exceptions.IdNotFound):
                return

        if 'container' in node['facts'].get('backends', []):
            children = utility.get_direct_children(node, api)
            for child in children:
                semaphore = 'nodes-id-%s' % child['id']
                utility.notify(semaphore)
        # Update transaction for node and children
        id_list = utility.fully_expand_nodelist([node], api)
        # TODO(shep): this needs to be better abstracted
    # Need a codepath to update transaction for attr modifications
    else:
        # TODO(shep): this needs to be better abstracted
        id_list = [node_id]
    _update_transaction_id('nodes', id_list)


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
        try:
            model_object = api._model_update_by_id(object_type, object_id,
                                                   flask.request.json)
        except exceptions.IdNotFound:
            return http_notfound(msg='not found')
        except exceptions.IdInvalid:
            return http_badrequest()

        _notify(model_object, object_type, object_id)

        return http_response(200, '%s Updated' % s_obj.capitalize(),
                             **{s_obj: model_object})
    elif flask.request.method == 'DELETE':
        try:
            model_object = api._model_get_by_id(object_type, object_id)
            if api._model_delete_by_id(object_type, object_id):
                _notify(model_object, object_type, object_id)
                return http_response(200, '%s deleted' % s_obj.capitalize())
        except exceptions.IdNotFound:
            return http_notfound(msg='not found')
        except exceptions.IdInvalid:
            return http_badrequest()
    elif flask.request.method == 'GET':
        if 'poll' in flask.request.args:
            # we're polling
            semaphore = '%s-id-%s' % (object_type, object_id)
            utility.wait(semaphore)

        try:
            model_object = api._model_get_by_id(object_type, object_id)
        except exceptions.IdNotFound:
            return http_notfound(msg='not found')
        except exceptions.IdInvalid:
            return http_badrequest()

        return http_response(200, 'success', **{s_obj: model_object})
    else:
        return http_notfound(msg='Unknown method %s' % flask.request.method)


@requires_auth()
def http_solver_request(node_id, constraints,
                        api=None, result=None, plan=None):
    if api is None:
        api = api_from_models()

    subtask = gevent.spawn(
        gevent.util.wrap_errors(
            (ValueError, exceptions.IdNotFound),
            utility.solve_and_run), node_id,
        constraints, api, plan)
    gevent.sleep(0)

    st_result = subtask.get(block=True, timeout=None)

    # this will either turn a 4-touple, or an exception.
    if isinstance(st_result, ValueError):
        return http_response(403, msg=str(st_result))
    elif isinstance(st_result, exceptions.IdNotFound):
        # push up the 404
        raise exceptions.IdNotFound
    else:
        task, is_solvable, requires_input, solution_plan = st_result

    if task is None:
        if ((not is_solvable) and requires_input):
            return http_conflict(msg='need additional input',
                                 plan=solution_plan,
                                 friendly='Please supply additional info')
        if not is_solvable:
            return http_response(403, msg='cannot be solved',
                                 friendly='Cannot solve action')

    # here we need to return the object (node/fact),
    # but should consequence be applied?!?
    # no, we are just going to return a bare 20x
    if result is None:
        result = {}

    result['plan'] = solution_plan
    result['task'] = task

    return http_response(202, 'executing change', **result)
