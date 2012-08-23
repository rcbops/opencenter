#!/usr/bin/env python
import sys

from flask import Flask, Response, request, session, jsonify, url_for

from database import db_session
from models import Nodes, Roles, Clusters

from ConfigParser import ConfigParser
from getopt import getopt, GetoptError
from pprint import pprint

import backends

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
    debug = False
    configfile = None
    daemonize = False
    config_hash = {}
    global backend

    bind_address = '0.0.0.0'
    bind_port = 8080

    def usage():
        print "%s: [options]\n"
        print "Options:"
        print " -c <configfile>         use exernal config"
        print " -d                      set debugging"

    try:
        opts, args = getopt(sys.argv[1:], "c:d")
    except GetoptError, e:
        print str(e)
        usage()
        sys.exit(1)

    for o, a in opts:
        if o == '-c':
            configfile = a
        elif o == '-d':
            debug = True
        else:
            usage()
            sys.exit(1)

    # read the config file
    if configfile:
        config = ConfigParser()
        config.read(configfile)

        config_hash = dict(
            [(s, dict(config.items(s))) for s in config.sections()])

        bind_address = config_hash['main'].get('bind_address', '0.0.0.0')
        bind_port = int(config_hash['main'].get('bind_port', '8080'))

        backend_module = config_hash['main'].get('backend', 'none')
        backend = backends.load(
            backend_module, config_hash.get('%s_backend' % backend_module), {})

    app.debug = debug
    app.run(host=bind_address, port=bind_port)
