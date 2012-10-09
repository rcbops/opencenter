#!/usr/bin/env python

import json
from pprint import pprint

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from db import api as api
from db import exceptions as exc
from db.database import db_session
from db.models import Clusters
from errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_not_implemented)

from filters import AstBuilder, FilterTokenizer

clusters = Blueprint('clusters', __name__)


@clusters.route('/', methods=['GET', 'POST'])
def list_clusters():
    if request.method == 'POST':
        fields = api.cluster_get_columns()
        data = dict((field, request.json[field] if (field in request.json)
                     else None) for field in fields)
        # FIXME(rp): get a role name and a node name, and
        # do a set_cluster_for_node(node_name, cluster_name)
        try:
            cluster = api.cluster_create(data)
            href = request.base_url + str(cluster['id'])
            msg = {'status': 201,
                   'message': 'Cluster Created',
                   'cluster': cluster,
                   'ref': href}
            resp = jsonify(msg)
            resp.status_code = 201
            resp.headers['Location'] = href
        except exc.CreateError, e:
            return http_bad_request(e.message)
    else:
        cluster_list = api.clusters_get_all()
        resp = jsonify({'clusters': cluster_list})
    return resp


@clusters.route('/filter', methods=['POST'])
def filter_clusters():
    builder = AstBuilder(FilterTokenizer(),
                         'clusters: %s' % request.json['filter'])
    return jsonify({'clusters': builder.eval()})


@clusters.route('/<cluster_id>/nodes', methods=['GET'])
def nodes_by_cluster_id(cluster_id):
    if request.method == 'GET':
        node_list = api.cluster_get_node_list(cluster_id)
        if node_list is None:
            return http_not_found()
        else:
            resp = jsonify({'nodes': node_list})
            return resp


@clusters.route('/<cluster_id>/<key>', methods=['GET', 'PUT'])
def attributes_by_cluster_id(cluster_id, key):
    cluster = api.cluster_get_by_id(cluster_id)
    if cluster is None:
        return http_not_found()
    else:
        if request.method == 'PUT':
            if key in ['id', 'name']:
                msg = "Attribute %s is not modifiable" % key
                return http_bad_request(msg)
            else:
                if key not in request.json:
                    msg = "Empty body"
                    return http_bad_request(msg)
                else:
                    data = {key: request.json[key]}
                    updated_cluster = api.cluster_update_by_id(
                        cluster_id,
                        data)
                    msg = {'status': 200,
                           'cluster': updated_cluster,
                           'message': 'Updated Attribute: %s' % key}
                    resp = jsonify(msg)
                    resp.status_code = 200
        else:
            resp = jsonify({key: cluster[key]})
        return resp


@clusters.route('/<cluster_id>/config', methods=['PATCH'])
def config_by_cluster_id(cluster_id):
    r = Clusters.query.filter_by(id=cluster_id).first()
    if r is None:
        return http_not_found()
    else:
        if request.method == 'PATCH':
            r.config = dict((k, v) for k, v in request.json.iteritems())
            try:
                db_session.commit()
                msg = {'status': 200,
                       'cluster': dict(
                           (c, getattr(r, c))
                           for c in r.__table__.columns.keys()),
                       'message': 'Updated Attribute: config'}
                resp = jsonify(msg)
                resp.status_code = 200
            except Exception, e:
                db_session.rollback()
                return http_conflict(e)
        return resp


@clusters.route('/<cluster_id>', methods=['GET', 'PUT', 'DELETE'])
def cluster_by_id(cluster_id):
    if request.method == 'PUT':
        fields = api.cluster_get_columns()
        data = dict((field, request.json[field]) for field in fields
                    if field in request.json)
        cluster = api.cluster_update_by_id(cluster_id, data)
        resp = jsonify({'cluster': cluster})
    elif request.method == 'DELETE':
        try:
            if api.cluster_delete_by_id(cluster_id):
                msg = {'status': 200, 'message': 'Cluster deleted'}
                resp = jsonify(msg)
                resp.status_code = 200
        except exc.NodeNotFound, e:
            return http_not_found()
    else:
        cluster = api.cluster_get_by_id(cluster_id)
        if cluster is None:
            return http_not_found()
        else:
            resp = jsonify({'cluster': cluster})
    return resp
