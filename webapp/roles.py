#!/usr/bin/env python

from flask import Blueprint, Flask, Response, request, abort
from flask import session, jsonify, url_for, current_app

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from db.database import db_session
from db.models import Nodes, Roles, Clusters

roles = Blueprint('roles', __name__)


@roles.route('/', methods=['GET', 'POST'])
def list_roles():
    if request.method == 'POST':
        if 'name' in request.json:
            name = request.json['name']
            desc = None
            if 'description' in request.json:
                desc = request.json['description']
            role = Roles(name, desc)
            db_session.add(role)
            try:
                db_session.commit()
                msg = {'status': 201, 'message': 'Role Created',
                       'role': dict((c, getattr(role, c))
                                    for c in role.__table__.columns.keys()),
                       'ref': request.url + url_for('roles.role_by_id',
                                                    role_id=role.id)}
                resp = jsonify(msg)
                resp.headers['location'] = request.url + url_for('roles.role_by_id',
                                                                 role_id=role.id)
                resp.status_code = 201
            except IntegrityError, e:
                msg = {'status': 500, "message": e.message}
                resp = jsonify(msg)
                resp.status_code = 500
        else:
            return bad_request("name")
        return resp
    else:
        role_list = dict(roles=[dict((c, getattr(r, c))
                         for c in r.__table__.columns.keys())
                         for r in Roles.query.all()])
        resp = jsonify(role_list)
        return resp


@roles.route('/<role_id>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def role_by_id(role_id):
    if request.method == 'PATCH' or request.method == 'POST':
        return not_implemented()
    elif request.method == 'PUT':
        r = Roles.query.filter_by(id=role_id).first()
        if 'name' in request.json:
            r.name = request.json['name']
        if 'description' in request.json:
            r.description = request.json['description']
        #TODO(shep): this is an un-excepted db call
        db_session.commit()
        resp = jsonify(dict((c, getattr(r, c))
                       for c in r.__table__.columns.keys()))
    elif request.method == 'DELETE':
        r = Roles.query.filter_by(id=role_id).first()
        try:
            db_session.delete(r)
            db_session.commit()
            msg = {'status': 200, 'message': 'Role deleted'}
            resp = jsonify(msg)
            resp.status_code = 200
        except UnmappedInstanceError, e:
            return not_found()
            # abort(404)
    else:
        r = Roles.query.filter_by(id=role_id).first()
        if r is None:
            # return errors.not_found()
            abort(404)
        else:
            resp = jsonify(dict((c, getattr(r, c))
                           for c in r.__table__.columns.keys()))
    return resp


@roles.errorhandler(404)
def not_found(error=None):
    msg = {
        'status': 404,
        'message': 'Not Found: ' + request.url}
    resp = jsonify(msg)
    resp.status_code = 404
    return resp


@roles.errorhandler(501)
def not_implemented(error=None):
    msg = {
        'status': 501,
        'message': 'Not Implemented'}
    resp = jsonify(msg)
    resp.status_code = 501
    return resp

@roles.errorhandler(400)
def bad_request(error=None):
    print "ERROR: %s" % error
    msg = {'status': 400,
           'message': "Attribute '%s' was not provided" % error}
    resp = jsonify(msg)
    resp.status_code = 400
    return resp
