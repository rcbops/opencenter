#!/usr/bin/env python
from flask import Flask, Response, request, session, jsonify, url_for

from database import db_session
from models import Nodes, Roles, Clusters

from pprint import pprint

app = Flask(__name__)
app.config['DEBUG'] = True


@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/roles', methods=['GET', 'POST'])
def list_roles():
    if request.method == 'POST':
        name = request.json['name']
        desc = request.json['description']

        role = Roles(name, desc)
        db_session.add(role)
        db_session.commit()

        message = {
            'status': 201,
            'message': 'Role Created',
            'role': dict((c, getattr(role, c))
                         for c in role.__table__.columns.keys()),
            'ref': url_for('role_by_id', role_id=role.id)
        }
        resp = jsonify(message)
        resp.status_code = 201
        return resp
    else:
        role_list = dict(roles=[dict((c, getattr(r, c))
                         for c in r.__table__.columns.keys())
                         for r in Roles.query.all()])
        resp = jsonify(role_list)
        return resp


@app.route('/roles/<role_id>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def role_by_id(role_id):
    if request.method == 'PUT':
        message = {
            'status': 501,
            'message': 'Not Implemented'
        }
        resp = jsonify(message)
        resp.status_code = 501
        return resp
    elif request.method == 'PATCH':
        message = {
            'status': 501,
            'message': 'Not Implemented'
        }
        resp = jsonify(message)
        resp.status_code = 501
        return resp
    elif request.method == 'DELETE':
        r = Roles.query.filter_by(id=role_id).first()
        db_session.delete(r)
        db_session.commit()
        return 'Deleted role: %s' % (role_id)
    else:
        r = Roles.query.filter_by(id=role_id).first()
        pprint(r)
        if r is None:
            resp = jsonify(dict())
        else:
            resp = jsonify(dict((c, getattr(r, c))
                           for c in r.__table__.columns.keys()))
        return resp


@app.route('/clusters', methods=['GET'])
def list_clusters():
    cluster_list = dict(clusters=[dict((c, getattr(r, c))
                        for c in r.__table__.columns.keys())
                        for r in Clusters.query.all()])
    resp = jsonify(cluster_list)
    return resp


@app.route('/nodes', methods=['GET', 'POST'])
def node():
    if request.method == 'POST':
        hostname = request.json['hostname']

        # Grab role_id from payload
        role_id = None
        if 'role_id' in request.json:
            role_id = request.json['role_id']

        # Grab cluster_id from payload
        cluster_id = None
        if 'cluster_id' in request.json:
            cluster_id = request.json['cluster_id']

        node = Nodes(hostname, role_id, cluster_id)
        # TODO(shep): need to break if IntegrityError is thrown
        db_session.add(node)
        db_session.commit()
        message = {
            'status': 201,
            'message': 'Node Created',
            'ref': url_for('node_by_id', node_id=node.id)
        }
        resp = jsonify(message)
        resp.status_code = 201
        return resp
    else:
        node_list = dict(nodes=[dict((c, getattr(r, c))
                         for c in r.__table__.columns.keys())
                         for r in Nodes.query.all()])
        resp = jsonify(node_list)
        return resp


@app.route('/nodes/<node_id>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def node_by_id(node_id):
    if request.method == 'PUT':
        message = {
            'status': 501,
            'message': 'Not Implemented'
        }
        resp = jsonify(message)
        resp.status_code = 501
        return resp
    elif request.method == 'PATCH':
        message = {
            'status': 501,
            'message': 'Not Implemented'
        }
        resp = jsonify(message)
        resp.status_code = 501
        return resp
    elif request.method == 'DELETE':
        r = Nodes.query.filter_by(id=node_id).first()
        db_session.delete(r)
        db_session.commit()
        return 'Deleted node: %s' % (node_id)
    elif request.method == 'GET':
        r = Nodes.query.filter_by(id=node_id).first()
        pprint(r)
        if r is None:
            resp = jsonify(dict())
        else:
            resp = jsonify(dict((c, getattr(r, c))
                           for c in r.__table__.columns.keys()))
        return resp

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
