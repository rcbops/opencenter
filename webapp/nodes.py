#!/usr/bin/env python

import json
from pprint import pprint

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from db.database import db_session
from db.models import Nodes, Roles, Clusters
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
                config = json.dumps(request.json['config'])

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
                    node_settings=request.json['config'])
                db_session.commit()
                n = dict()
                for col in node.__table__.columns.keys():
                    if col == 'config':
                        tmp = getattr(node, col)
                        n[col] = tmp if (tmp is None) else json.loads(tmp)
                    else:
                        n[col] = getattr(node, col)
                href = request.base_url + str(node.id)
                msg = {'status': 201,
                       'message': 'Node Created',
                       'node': n,
                       'ref': href}
                resp = jsonify(msg)
                resp.headers['Location'] = href
                resp.status_code = 201
            except IntegrityError, e:
                db_session.rollback()
                return http_conflict(e)
        else:
            return http_bad_request('hostname')
    else:
        node_list = {"nodes": []}
        for row in Nodes.query.all():
            tmp = dict()
            for col in row.__table__.columns.keys():
                if col == 'config':
                    val = getattr(row, col)
                    tmp[col] = val if (val is None) else json.loads(val)
                else:
                    tmp[col] = getattr(row, col)
            node_list['nodes'].append(tmp)
        resp = jsonify(node_list)
    return resp


@nodes.route('/<node_id>/tasks', methods=['GET', 'PUT'])
def tasks_by_node_id(node_id):
    # Display only tasks with state=pending
    pass

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
            r.config = json.dumps(request.json['config'])
        #TODO(shep): this is an un-excepted db call
        db_session.commit()
        node = dict()
        for col in r.__table__.columns.keys():
            if col == 'config':
                val = getattr(r,col)
                node[col] = val if (val is None) else json.loads(val)
            else:
                node[col] = getattr(r, col)
        resp = jsonify(node)
    elif request.method == 'DELETE':
        r = Nodes.query.filter_by(id=node_id).first()
        try:
            db_session.delete(r)
            db_session.commit()

            # FIXME(rp): transaction
            current_app.backend.delete_node(r.hostname)

            msg = {'status': 200, 'message': 'Node deleted'}
            resp = jsonify(msg)
            resp.status_code = 200
        except UnmappedInstanceError, e:
            return http_not_found()
    else:
        row = Nodes.query.filter_by(id=node_id).first()
        if row is None:
            return http_not_found()
        else:
            node = dict()
            for col in row.__table__.columns.keys():
                if col == 'config':
                    val = getattr(row, col)
                    node[col] = val if (val is None) else json.loads(val)
                else:
                    node[col] = getattr(row, col)
            resp = jsonify(node)
    return resp
