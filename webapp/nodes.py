#!/usr/bin/env python

import json
from pprint import pprint

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

# import db.api as api
from db import api as api
from db import exceptions as exc
from db.database import db_session
from db.models import Nodes, Roles, Clusters, Tasks

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
        fields = ['hostname', 'role_id', 'cluster_id', 'backend',
                  'backend_state', 'config']
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

@nodes.route('/schema', methods=['GET'])
def schema():
    return jsonify(api._model_get_schema('nodes'))

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
    return http_not_implemented

@nodes.route('/<node_id>', methods=['GET', 'PUT', 'DELETE'])
def node_by_id(node_id):
    resp = ''

    if request.method == 'PUT':
        # NOTE: We probably can't rename hosts -- it affect chef...
        # Think on this.  Also, probably should do a get_node_status
        # to make sure it's happy in the config management
        r = Nodes.query.filter_by(id=node_id).first()
        if 'hostname' in request.json:
            r.hostname = request.json['hostname']
        if 'cluster_id' in request.json:
            r.cluster_id = request.json['cluster_id']
        if 'role_id' in request.json:
            r.role_id = request.json['role_id']
        if 'config' in request.json:
            r.config = request.json['config']
        #TODO(shep): this is an un-excepted db call
        db_session.commit()
        node = dict(node=dict((c, getattr(r, c))
                              for c in r.__table__.columns.keys()))
        resp = jsonify(node)
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
