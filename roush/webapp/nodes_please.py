#!/usr/bin/env python

import flask
import generic

from roush.db.api import api_from_models

from roush.webapp import ast
from roush.webapp import utility
from roush.webapp import errors
from roush.webapp import auth

import roush.webapp.nodes


api = api_from_models()
object_type = 'nodes'
bp = flask.Blueprint('%s_please' % object_type,  __name__)


# strategy:  we'll basically just fall through to the
# underlying nodes methods, but we'll special case
# the CRUD operators for nodes to shoehorn solving into
# the process.
def dict_differ(old, new):
    result = {}
    for key in new:
        if not key in old:
            pass
        if new[key] != old[key]:
            result[key] = new[key]

    return result


@bp.route('/', methods=['GET'])
def list():
    return roush.webapp.nodes.list()


# FIXME(rp): we should allow for config type node creation.
@bp.route('/', methods=['POST'])
def create():
    return generic.http_response(
        403, 'cannot create nodes right now.  sorry.',
        friendly='no node creation')


@bp.route('/<object_id>', methods=['GET'])
def by_id(object_id):
    return roush.webapp.nodes.by_id(object_id)


# FIXME(rp): again, should be able to delete appropriate containers
# or perhaps generic deletion should be solvable.
@bp.route('/<object_id>', methods=['DELETE'])
def delete_id(object_id):
    return generic.http_response(
        403, 'cannot delete nodes right now',
        friendly='no node deletation')


@bp.route('/<object_id>', methods=['PUT'])
def put_id(object_id):
    """
    there are two general kinds of node updation: those that
    must be solved for, and those that do not need to be solved for.

    Currently, only parent_id changes need to be solved for.  (this
    is perhaps a hint that parent_id needs to be a fact, not a
    direct node attribute... think on this.
    """
    existing = api.node_get_by_id(object_id)
    if existing is None:
        return generic.http_notfound()

    data = flask.request.json

    changes = dict_differ(existing, data)
    if 'facts' in changes:
        changes.pop('facts')

    if 'attrs' in changes:
        changes.pop('attrs')

    changes.pop('id')

    flask.current_app.logger.debug('Change set for PUT: %s' % changes)

    if 'parent_id' in changes:
        # need to solve
        if len(changes) > 1:
            return generic.http_response(
                403, 'cannot change parent and other data simultaneously',
                friendly='no node update across solver boundary')

        # solve it all up
        constraints = ["parent_id=%s" % data['parent_id']]

        # This really isn't right.  We should return
        # node with consequences expressed.
        return generic.http_solver_request(
            object_id, constraints, api=api)
    else:
        # fall through to underlying put
        return nodes.by_id(object_id)


@bp.route('/<node_id>/tasks_blocking', methods=['GET'])
def tasks_blocking_by_node_id(node_id):
    return nodes.task_blocking_by_node_id(node_id)


@bp.route('/<node_id>/tasks', methods=['GET'])
def tasks_by_node_id(node_id):
    return nodes.tasks_by_node_id(node_id)


@bp.route('/<node_id>/adventures', methods=['GET'])
def adventures_by_node_id(node_id):
    return nodes.adventures_by_node_id(node_id)


@bp.route('/<node_id>/tree', methods=['GET'])
def tree_by_id(node_id):
    return nodes.tree_by_id(node_id)
