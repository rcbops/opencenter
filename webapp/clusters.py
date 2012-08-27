#!/usr/bin/env python

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

clusters = Blueprint('clusters', __name__)


@clusters.route('/', methods=['GET', 'POST'])
def list_clusters():
    if request.method == 'POST':
        if 'name' in request.json:
            name = request.json['name']
            desc = None
            if 'description' in request.json:
                desc = request.json['description']
            cluster = Clusters(name=name, description=desc)
            db_session.add(cluster)
            try:
                # FIXME(rp): Transactional problem
                db_session.commit()
                current_app.backend.create_cluster(name)

                # FIXME(rp): do set_cluster_settings if have json
                msg = {'status': 201, 'message': 'Cluster Created',
                       'cluster': dict((c, getattr(cluster, c))
                                       for c in cluster.__table__.columns.keys()),
                       'ref': url_for('clusters.cluster_by_id',
                                      cluster_id=cluster.id)}
                resp = jsonify(msg)
                resp.status_code = 201
            except IntegrityError, e:
                return http_conflict(e)
        else:
            return http_bad_request('name')
    else:
        cluster_list = dict(clusters=[dict((c, getattr(r, c))
                            for c in r.__table__.columns.keys())
                            for r in Clusters.query.all()])
        resp = jsonify(cluster_list)
    return resp


@clusters.route('/<cluster_id>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def cluster_by_id(cluster_id):
    if request.method == 'PATCH' or request.method == 'POST':
        return http_not_implemented()
    elif request.method == 'PUT':
        r = Clusters.query.filter_by(id=cluster_id).first()
        # FIXME(rp): renames break the backend association
        if 'name' in request.json:
            r.name = request.json['name']
        if 'description' in request.json:
            r.description = request.json['description']
        #TODO(shep): this is an un-excepted db call
        db_session.commit()
        resp = jsonify(dict((c, getattr(r, c))
                       for c in r.__table__.columns.keys()))
    elif request.method == 'DELETE':
        r = Clusters.query.filter_by(id=cluster_id).first()
        try:
            db_session.delete(r)
            db_session.commit()

            # FIXME(rp): Transaction
            current_app.backend.delete_cluster(r.name)

            msg = {'status': 200, 'message': 'Cluster deleted'}

            resp = jsonify(msg)
            resp.status_code = 200
        except UnmappedInstanceError, e:
            return http_not_found()
    else:
        r = Clusters.query.filter_by(id=cluster_id).first()
        if r is None:
            return http_not_found()
        else:
            resp = jsonify(dict((c, getattr(r, c))
                           for c in r.__table__.columns.keys()))
    return resp
