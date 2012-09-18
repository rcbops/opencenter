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

nodes = Blueprint('nodes', __name__)


@nodes.route('/', methods=['GET', 'POST'])
def list_nodes():
    if request.method == 'POST':
        if 'hostname' in request.json:
            hostname = request.json['hostname']

            role_id = None
            if 'role_id' in request.json:
                role_id = request.json['role_id']

            cluster_id = None
            if 'cluster_id' in request.json:
                cluster_id = request.json['cluster_id']

            config = None
            if 'config' in request.json:
                config = request.json['config']

            # This should probably check against Roles.id and Clusters.id
            node = Nodes(hostname=hostname, role_id=role_id,
                         cluster_id=cluster_id, config=config)

            # FIXME(rp): get a role name and a node name, and
            # do a set_cluster_for_node(node_name, cluster_name)
            try:
                db_session.add(node)
                current_app.backend.create_node(
                    node.hostname,
                    role=node.role_id,
                    cluster=node.cluster_id,
                    node_settings=node.config)
                db_session.commit()
                href = request.base_url + str(node.id)
                msg = {'status': 201,
                       'message': 'Node Created',
                       'node': dict(
                           (c, getattr(node, c))
                           for c in node.__table__.columns.keys()),
                       'ref': href}
                resp = jsonify(msg)
                resp.headers['Location'] = href
                resp.status_code = 201
            except IntegrityError, e:
                db_session.rollback()
                return http_conflict(e)
        else:
            return http_bad_request('Attribute hostname not provided')
    else:
        nodes = api.nodes_get_all()
        resp = jsonify({'nodes': nodes})
    return resp


@nodes.route('/<node_id>/tasks', methods=['GET', 'PUT'])
def tasks_by_node_id(node_id):
    # Display only tasks with state=pending
    row = Tasks.query.filter_by(node_id=node_id,
                                state='pending').first()
    if row is None:
        return http_not_found()
    else:
        task = dict()
        for col in row.__table__.columns.keys():
            if col == 'payload' or col == 'result':
                val = getattr(row, col)
                task[col] = val if (val is None) else json.loads(val)
            else:
                task[col] = getattr(row, col)

        resp = jsonify(task)
        return resp


@nodes.route('/<node_id>', methods=['GET', 'PUT', 'DELETE'])
def node_by_id(node_id):
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
        # node = api.node_get_by_filter('id', node_id)
        node = api.node_get_by_id(node_id)
        if not node:
            return http_not_found()
        else:
            resp = jsonify({'node': node})
    return resp
