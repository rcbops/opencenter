#!/usr/bin/env python

import json
from pprint import pprint

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

# import db.api as api
from db import api as api
from db import exceptions as exc
from db.database import db_session
from db.models import Nodes, Roles, Clusters, Tasks, Adventures

from errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_not_implemented)

from filters import AstBuilder, FilterTokenizer

nodes = Blueprint('nodes', __name__)


@nodes.route('/', methods=['GET', 'POST'])
def list_nodes():
    if request.method == 'POST':
        fields = api.node_get_columns()
        data = dict((field, request.json[field] if (field in request.json)
                     else None) for field in fields)
        # FIXME(rp): get a role name and a node name, and
        # do a set_cluster_for_node(node_name, cluster_name)
        try:
            node = api.node_create(data)
            current_app.backend.create_node(
                node['hostname'],
                role=node['role_id'],
                cluster=node['cluster_id'],
                node_settings=node['config'])
            if node['cluster_id'] is not None:
                cluster = api.cluster_get_by_id(node['cluster_id'])
                current_app.backend.set_cluster_for_node(
                    node=node['hostname'],
                    cluster=cluster['name'])
            href = request.base_url + str(node['id'])
            msg = {'status': 201,
                   'message': 'Node Created',
                   'node': node,
                   'ref': href}
            resp = jsonify(msg)
            resp.status_code = 201
            resp.headers['Location'] = href
        except exc.CreateError, e:
            return http_bad_request(e.message)
    else:
        nodes = api.nodes_get_all()
        resp = jsonify({'nodes': nodes})
    return resp


@nodes.route('/filter', methods=['POST'])
def filter_nodes():
    builder = AstBuilder(FilterTokenizer(),
                         'nodes: %s' % request.json['filter'])
    return jsonify({'nodes': builder.eval()})


@nodes.route('/<node_id>/tasks', methods=['GET', 'PUT'])
def tasks_by_node_id(node_id):
    # Display only tasks with state=pending
    task = api.task_get_by_filter({'node_id': node_id, 'state': 'pending'})
    if not task:
        return http_not_found()
    else:
        resp = jsonify({'task': task})
        return resp


@nodes.route('/<node_id>/adventures', methods=['GET'])
def adventures_by_node_id(node_id):
    node = api.node_get_by_id(node_id)
    if not node:
        return http_not_found()
    else:
        adventures = api.adventures_get_by_node_id(node_id)
        resp = jsonify({'adventures': adventures})
    return resp


@nodes.route('/<node_id>', methods=['GET', 'PUT', 'DELETE'])
def node_by_id(node_id):
    resp = ''

    if request.method == 'PUT':
        fields = api.node_get_columns()
        data = dict((field, request.json[field]) for field in fields
                    if field in request.json)
        # NOTE: We probably can't rename hosts -- it affect chef...
        # Think on this.  Also, probably should do a get_node_status
        # to make sure it's happy in the config management
        node = api.node_update_by_id(node_id, data)
        resp = jsonify({'node': node})
    elif request.method == 'DELETE':
        try:
            # NOTE: This is a transactional problem
            # node = api.node_get_by_filter('id', node_id)
            node = api.node_get_by_id(node_id)
            if api.node_delete_by_id(node_id):
                current_app.backend.delete_node(node['hostname'])
                msg = {'status': 200, 'message': 'Node deleted'}
                resp = jsonify(msg)
                resp.status_code = 200
        except exc.NodeNotFound, e:
            return http_not_found()
    else:
        # node = api.node_get_by_filter({'id': node_id})
        node = api.node_get_by_id(node_id)
        if not node:
            return http_not_found()
        else:
            resp = jsonify({'node': node})
    return resp
