#!/usr/bin/env python

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from db.database import db_session
from db.models import Nodes, Roles, Clusters

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
                msg = {'status': 500, "message": e.message}
                resp = jsonify(msg)
                resp.status_code = 500
        else:
            msg = {'status': 400,
                   'message': "Attribute 'name' was not provided"}
            resp = jsonify(msg)
            resp.status_code = 400
    else:
        cluster_list = dict(clusters=[dict((c, getattr(r, c))
                            for c in r.__table__.columns.keys())
                            for r in Clusters.query.all()])
        resp = jsonify(cluster_list)
    return resp


@clusters.route('/<cluster_id>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def cluster_by_id(cluster_id):
    if request.method == 'PATCH' or request.method == 'POST':
        message = {
            'status': 501,
            'message': 'Not Implemented'
        }
        resp = jsonify(message)
        resp.status_code = 501
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
            msg = {'status': 404, 'message': 'Resource not found',
                   'cluster': {'id': cluster_id}}
            resp = jsonify(msg)
            resp.status_code = 404
    else:
        r = Clusters.query.filter_by(id=cluster_id).first()
        if r is None:
            msg = {'status': 404, 'message': 'Resource not found',
                   'cluster': {'id': cluster_id}}
            resp = jsonify(msg)
            resp.status_code = 404
        else:
            resp = jsonify(dict((c, getattr(r, c))
                           for c in r.__table__.columns.keys()))
    return resp
