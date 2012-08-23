#!/usr/bin/env python

import sys

from flask import Flask, Response, request, session, jsonify

from database import db_session
from models import Nodes, Roles, Clusters

from ConfigParser import ConfigParser
from getopt import getopt, GetoptError
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
    debug = False
    configfile = None
    daemonize = False
    config_hash = {}

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

    for o,a in opts:
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

        config_hash = { i: dict(config._sections[i]) for i in config._sections }

        bind_address = config_hash['main'].get('bind_address', '0.0.0.0')
        bind_port = int(config_hash['main'].get('bind_port', '8080'))

    app.debug = debug
    app.run(host=bind_address, port=bind_port)
