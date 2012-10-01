#!/usr/bin/env python

import json
from pprint import pprint

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError

# import db.api as api
from db import api as api
from db import exceptions as exc
from db.database import db_session
from db.models import Adventures
from errors import (
    http_bad_request,
    http_conflict,
    http_not_found,
    http_not_implemented)

adventures = Blueprint('adventures', __name__)


@adventures.route('/', methods=['GET', 'POST'])
def list_adventures():
    if request.method == 'POST':
        fields = ['name', 'language', 'dsl', 'backend', 'backend_state']
        data = {}
        for field in fields:
            if field in request.json:
                data[field] = request.json[field]
            else:
                data[field] = None
        try:
            adventure = api.adventure_create(data)
            href = request.base_url + str(adventure['id'])
            msg = {'status': 201, 'message': 'Adventure Create',
                   'ref': href,
                   'adventure': adventure}
            resp = jsonify(msg)
            resp.status_code = 201
            resp.headers['Location'] = href
        except exc.CreateError, e:
            return http_bad_request(e.message)
    else:
        adventures = api.adventures_get_all()
        resp = jsonify({'adventures': adventures})
    return resp


@adventures.route('/filter', methods=['POST'])
def filter_adventures():
    builder = AstBuilder(FilterTokenizer(),
                         'adventures: %s' % request.json['filter'])
    return jsonify({'adventures': builder.eval()})


@adventures.route('/<adventure_id>', methods=['GET', 'PUT', 'DELETE'])
def adventure_by_id(adventure_id):
    if request.method == 'PUT':
        pass
    elif request.method == 'DELETE':
        try:
            api.adventure_delete_by_id(adventure_id)
            msg = {'status': 200, 'message': 'Adventure deleted'}
            resp = jsonify(msg)
            resp.status_code = 200
        except exc.AdventureNotFound, e:
            return http_not_found()
    else:
        adventure = api.adventure_get_by_id(adventure_id)
        if not adventure:
            return http_not_found()
        else:
            resp = jsonify({'adventure': adventure})
    return resp
