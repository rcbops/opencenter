#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

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
