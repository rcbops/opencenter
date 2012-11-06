#!/usr/bin/env python

import flask

index = flask.Blueprint('index', __name__)


@index.route('/', methods=['GET'])
def list_index():
    url = flask.request.url

    msg = {
        'url': flask.request.url,
        'resources': {
            'clusters': {'url': url + 'clusters/'},
            'nodes': {'url': url + 'nodes/'},
            'roles': {'url': url + 'roles/'}},
        'there_is_not_enough_keystone_up_in_this_bitch': True}
    resp = flask.jsonify(msg)
    resp.status_code = 200
    return resp
