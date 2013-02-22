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

from flask import request, jsonify


def http_not_found(error=None):
    msg = {
        'status': 404,
        'message': 'Not Found: ' + request.url}
    resp = jsonify(msg)
    resp.status_code = 404
    return resp


def http_not_implemented(error=None):
    msg = {
        'status': 501,
        'message': 'Not Implemented'}
    resp = jsonify(msg)
    resp.status_code = 501
    return resp


def http_bad_request(msg):
    msg = {'status': 400,
           'message': msg}
    resp = jsonify(msg)
    resp.status_code = 400
    return resp


def http_conflict(error):
    msg = {'status': 409, "message": error.message}
    resp = jsonify(msg)
    resp.status_code = 409
    return resp
