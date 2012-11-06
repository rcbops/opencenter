#!/usr/bin/env python

from flask import Blueprint, request, jsonify


index = Blueprint('index', __name__)


@index.route('/', methods=['GET'])
def list_index():
    msg = {
        'url': request.url,
        'resources': {
            'clusters': {'url': request.url + 'clusters/'},
            'nodes': {'url': request.url + 'nodes/'},
            'roles': {'url': request.url + 'roles/'}},
        'there_is_not_enough_keystone_up_in_this_bitch': True}
    resp = jsonify(msg)
    resp.status_code = 200
    return resp
