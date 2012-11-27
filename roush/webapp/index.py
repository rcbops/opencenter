#!/usr/bin/env python

import flask
from roush.webapp import generic
from roush.db.api import api_from_models


bp = flask.Blueprint('index', __name__)


@bp.route('/', methods=['GET'])
def list_index():
    api = api_from_models()
    models = api._get_models()
    url = flask.request.url

    msg = {'url': flask.request.url,
           'resources': {}}

    for model in models:
        msg['resources'][model] = {'url': '%s%s/' % (url, model)}

    resp = flask.jsonify(msg)
    resp.status_code = 200
    return resp
