#!/usr/bin/env python

from flask import Blueprint, Flask, Response, request
from flask import jsonify, url_for, current_app


index = Blueprint('index', __name__)


@index.route('/', methods=['GET'])
def list_index():
    msg = {
        'url': request.url,
        'resources': {
            'clusters': {'url': request.url + 'clusters/'},
            'nodes': {'url': request.url + 'nodes/'},
            'roles': {'url': request.url + 'roles/'}}}
    resp = jsonify(msg)
    resp.status_code = 200
    return resp
