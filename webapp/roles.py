#!/usr/bin/env python

from flask import Blueprint, Flask, Response, request, abort
from flask import session, jsonify, url_for, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

from db import api as api
from db import exceptions as exc
from db.database import db_session
from db.models import Nodes, Roles, Clusters
from errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_not_implemented)

roles = Blueprint('roles', __name__)


@roles.route('/', methods=['GET', 'POST'])
def list_roles():
    if request.method == 'POST':
        fields = api.role_get_columns()
        data = dict((field, request.json[field] if (field in request.json)
                     else None) for field in fields)
        try:
            role = api.role_create(data)
            href = request.base_url + str(role['id'])
            msg = {'status': 201,
                   'message': 'Role Created',
                   'role': role,
                   'ref': href}
            resp = jsonify(msg)
            resp.status_code = 201
            resp.headers['Location'] = href
        except exc.CreateError, e:
            return http_bad_request(e.message)
    else:
        roles = api.roles_get_all()
        resp = jsonify({'roles': roles})
    return resp


@roles.route('/filter', methods=['POST'])
def filter_roles():
    builder = AstBuilder(FilterTokenizer(),
                         'roles: %s' % request.json['filter'])
    return jsonify({'roles': builder.eval()})


@roles.route('/<role_id>/<key>', methods=['GET', 'PUT'])
def attributes_by_role_id(role_id, key):
    role = api.role_get_by_id(role_id)
    if not role:
        return http_not_found()
    else:
        if request.method == 'PUT':
            if key in ['id', 'hostname']:
                msg = "Attribute %s is not modifiable" % key
                return http_bad_request(msg)
            else:
                if key not in request.json:
                    msg = "Empty body"
                    return http_bad_request(msg)
                else:
                    data = {key: request.json[key]}
                    updated_role = api.role_update_by_id(role_id, data)
                    msg = {'status': 200,
                           'role': updated_role,
                           'message': 'Updated Attribute: %s' % key}
                    resp = jsonify(msg)
                    resp.status_code = 200
        else:
            resp = jsonify({key: role[key]})
        return resp


@roles.route('/<role_id>', methods=['GET', 'PUT', 'DELETE'])
def role_by_id(role_id):
    if request.method == 'PUT':
        fields = api.role_get_columns()
        data = dict((field, request.json[field]) for field in fields
                    if field in request.json)
        role = api.role_update_by_id(role_id, data)
        resp = jsonify({'role': role})
    elif request.method == 'DELETE':
        try:
            if api.role_delete_by_id(role_id):
                msg = {'status': 200, 'message': 'Role deleted'}
                resp = jsonify(msg)
                resp.status_code = 200
        except exc.NodeNotFound, e:
            return http_not_found()
    else:
        role = api.role_get_by_id(role_id)
        if not role:
            return http_not_found()
        else:
            resp = jsonify({'role': role})
    return resp
