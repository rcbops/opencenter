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

import flask

from opencenter.db.api import api_from_models
from opencenter.webapp import generic


object_type = 'facts'
singular_object_type = generic.singularize(object_type)

bp = flask.Blueprint('%s_please' % object_type, __name__)


@bp.route('/', methods=['GET'])
def list():
    return generic.list(object_type)


@bp.route('/', methods=['POST'])
def create():
    old_fact = None

    # if we are creating with the same host_id and key, then we'll just update
    # fields = api._model_get_columns(object_type)

    api = api_from_models()
    data = flask.request.json

    if 'node_id' in data and 'key' in data:
        old_fact = api._model_get_first_by_query(
            object_type, 'node_id=%d and key="%s"' % (
                int(data['node_id']), data['key']))

    if old_fact:
        return modify_fact(old_fact['id'])

    # here, if the fact is a fact on a container,
    # we need to solve for fact application on all
    # child nodes.  <eek>
    #
    # FIXME(rp): so we'll punt for now, and just refuse fact
    # creates on containers.
    children = api._model_query('nodes',
                                'facts.parent_id = %s' % data['node_id'])
    if len(children) > 0:
        return generic.http_response(403,
                                     msg='cannot set fact on containers',
                                     friendly='oopsie')

    constraints = ['facts.%s = "%s"' %
                   (data['key'],
                    data['value'])]

    return generic.http_solver_request(
        data['node_id'], constraints, api=api,
        result={'fact': {'id': -1,
                         'node_id': data['node_id'],
                         'key': data['key'],
                         'value': data['value']}})


@bp.route('/<object_id>', methods=['GET'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)


@bp.route('/<object_id>', methods=['PUT'])
def modify_fact(object_id):
    """
    Express a fact modification as a list of constraints
    on the linked node.facts, and run the solved
    result
    """
    data = flask.request.json
    api = api_from_models()

    model_object = api._model_get_by_id('facts', object_id)
    if not model_object:
        return generic.http_notfound()

    node_id = model_object['node_id']

    # FIXME: TYPECASTING WHEN WE HAVE FACT TYPES
    constraints = ['facts.%s = "%s"' %
                   (model_object['key'],
                    data['value'])]

    return generic.http_solver_request(
        node_id, constraints, api=api,
        result={'fact': {'id': model_object['id'],
                         'node_id': node_id,
                         'key': model_object['key'],
                         'value': data['value']}})


@bp.route('/<object_id>', methods=['DELETE'])
def delete_object(object_id):
    msg = 'objects of type %s can not be deleted' % object_type
    return generic.http_notfound(msg=msg)
