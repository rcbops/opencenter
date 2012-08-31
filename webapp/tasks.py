#!/usr/bin/env python

import json
from pprint import pprint

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from db.database import db_session
from db.models import Nodes, Roles, Clusters, Tasks
from errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_not_implemented)

tasks = Blueprint('tasks', __name__)


@tasks.route('/', methods=['GET', 'POST'])
def list_tasks():
    if request.method == 'POST':
        msg = {'message': 'POST Method not implemented',
               'status': 501}
        resp = jsonify(msg)
        resp.status_code = 501
        if 'node_id' in request.json:
            action = request.json['node_id']

#            role_id = None
#            if 'role_id' in request.json:
#                role_id = request.json['role_id']
#
#            cluster_id = None
#            if 'cluster_id' in request.json:
#                cluster_id = request.json['cluster_id']
#
#            config = None
#            if 'config' in request.json:
#                config = json.dumps(request.json['config'])
#
#            # This should probably check against Roles.id and Clusters.id
#            node = Nodes(hostname=hostname, role_id=role_id,
#                         cluster_id=cluster_id, config=config)
#
#            # FIXME(rp): get a role name and a node name, and
#            # do a set_cluster_for_node(node_name, cluster_name)
#            try:
#                db_session.add(node)
#                current_app.backend.create_node(
#                    node.hostname,
#                    role=node.role_id,
#                    cluster=node.cluster_id,
#                    node_settings=config)
#                db_session.commit()
#                n = dict()
#                for col in node.__table__.columns.keys():
#                    if col == 'config':
#                        tmp = getattr(node, col)
#                        n[col] = tmp if (tmp is None) else json.loads(tmp)
#                    else:
#                        n[col] = getattr(node, col)
#                href = request.base_url + str(node.id)
#                msg = {'status': 201,
#                       'message': 'Node Created',
#                       'node': n,
#                       'ref': href}
#                resp = jsonify(msg)
#                resp.headers['Location'] = href
#                resp.status_code = 201
#            except IntegrityError, e:
#                db_session.rollback()
#                return http_conflict(e)
        else:
            return http_bad_request('node_id')
    else:
        task_list = {"tasks": []}
        for row in Tasks.query.all():
            tmp = dict()
            for col in row.__table__.columns.keys():
                if col == 'payload' or col == 'result':
                    val = getattr(row, col)
                    tmp[col] = val if (val is None) else json.loads(val)
                else:
                    tmp[col] = getattr(row, col)
            task_list['tasks'].append(tmp)
        resp = jsonify(task_list)
    return resp


@tasks.route('/<task_id>', methods=['GET', 'PUT'])
def task_by_id(task_id):
    if request.method == 'PUT':
        # NOTE: We probably can't rename hosts -- it affect chef...
        # Think on this.  Also, probably should do a get_node_status
        # to make sure it's happy in the config management
        r = Tasks.query.filter_by(id=node_id).first()
        if 'action' in request.json:
            r.action = request.json['action']
        if 'payload' in request.json:
            r.payload = jason.dumps(request.json['payload'])
        if 'state' in request.json:
            r.state = request.json['state']
        if 'result' in request.json:
            r.result = json.dumps(request.json['result'])
        #TODO(shep): this is an un-excepted db call
        db_session.commit()
        task = dict()
        for col in r.__table__.columns.keys():
            if col == 'payload' or col == 'result':
                val = getattr(r,col)
                task[col] = val if (val is None) else json.loads(val)
            else:
                task[col] = getattr(r, col)
        resp = jsonify(task)
    else:
        row = Tasks.query.filter_by(id=task_id).first()
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
