#!/usr/bin/env python

import generic
import flask

from roush.db.api import api_from_models


api = api_from_models()
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

    data = flask.request.json

    model_object = None

    if 'node_id' in data and 'key' in data:
        old_fact = api._model_get_first_by_filter(object_type,
                                                  {'node_id': data['node_id'],
                                                   'key': data['key']})

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
    return generic.http_response(404, 'objects of type %s cannot be deleted' %
                                 object_type)
