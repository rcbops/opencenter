#!/usr/bin/env python

from flask import Flask, Response, request, session, jsonify

from database import db_session
from models import Nodes, Roles, Clusters

from pprint import pprint

app = Flask(__name__)
app.config['DEBUG'] = True


@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/roles', methods=['GET'])
def list_roles():
    role_list = dict(roles=[dict((c, getattr(r, c))
                     for c in r.__table__.columns.keys())
                     for r in Roles.query.all()])
    resp = jsonify(role_list)
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
    if request.method == 'GET':
        node_list = dict(nodes=[dict((c, getattr(r, c))
                         for c in r.__table__.columns.keys())
                         for r in Nodes.query.all()])
        resp = jsonify(node_list)
        return resp
    elif request.method == 'POST':
        node = Nodes(request.json['hostname'])
        db_session.add(node)
        db_session.commit()
        return 'Created new node: %s' % (request.json['hostname'])


@app.route('/nodes/<node_id>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def show_node(node_id):
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
        r = Nodes.query.filter_by(id=1).first()
        db_session.delete(r)
        db_session.commit()
        return 'Deleted node: %s' % (node_id)
    elif request.method == 'GET':
        r = Nodes.query.filter_by(id=1).first()
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
