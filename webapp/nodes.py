#!/usr/bin/env python
from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from database import db_session
from models import Nodes, Roles, Clusters

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

            # This should probably check against Roles.id and Clusters.id
            node = Nodes(hostname=hostname, role_id=role_id, cluster_id=cluster_id)

            # FIXME(rp): get a role name and a node name, and
            # do a set_cluster_for_node(node_name, cluster_name)

            db_session.add(node)
            try:
                db_session.commit()
                message = {'status': 201, 'message': 'Node Created',
                           'cluster': dict((c, getattr(node, c))
                                           for c in node.__table__.columns.keys()),
                    'ref': url_for('node_by_id', node_id=node.id)
                }
                resp = jsonify(message)
                resp.status_code = 201
            except IntegrityError, e:
                msg = {'status': 500, "message": e.message}
                resp = jsonify(msg)
                resp.status_code = 500
        else:
            msg = {'status': 400, "message": "Attribute 'name' was not provided"}
            resp = jsonify(msg)
            resp.status_code = 400
    else:
        node_list = dict(nodes=[dict((c, getattr(r, c))
                         for c in r.__table__.columns.keys())
                         for r in Nodes.query.all()])
        resp = jsonify(node_list)
    return resp


@nodes.route('/<node_id>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def node_by_id(node_id):
    if request.method == 'PATCH' or request.method == 'POST':
        message = {
            'status': 501,
            'message': 'Not Implemented'
        }
        resp = jsonify(message)
        resp.status_code = 501
    elif request.method == 'PUT':
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
        #TODO(shep): this is an un-excepted db call
        db_session.commit()
        resp = jsonify(dict((c, getattr(r, c))
                       for c in r.__table__.columns.keys()))
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
            msg = {'status': 404, 'message': 'Resource not found',
                   'node': {'id': node_id}}
            resp = jsonify(msg)
            resp.status_code = 404
    else:
        r = Nodes.query.filter_by(id=node_id).first()
        if r is None:
            msg = {'status': 404, 'message': 'Resource not found',
                   'node': {'id': node_id}}
            resp = jsonify(msg)
            resp.status_code = 404
        else:
            resp = jsonify(dict((c, getattr(r, c))
                           for c in r.__table__.columns.keys()))
    return resp
