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

import sys

from flask import request
from gevent.pywsgi import WSGIServer

from roush.db.database import init_db
from roush.webapp import Thing
from roush.webapp.auth import is_allowed, authenticate

def main():
    foo = Thing("roush", argv=sys.argv[1:], configfile='local.conf',
                debug=True)

    @foo.after_request
    def allow_cors(response):
        if 'cors_uri' in foo.config and \
                'Origin' in request.headers and \
                request.headers['Origin'] in foo.config['cors_uri']:
            response.headers['Access-Control-Allow-Origin'] = \
                request.headers['Origin']
            response.headers['Access-Control-Allow-Methods'] = \
                'HEAD,GET,PUT,POST,OPTIONS,DELETE'
            response.headers['Access-Control-Allow-Headers'] = \
                'Content-Type'
        return response

    @foo.before_request
    def auth_f():
        if not is_allowed(roles=None):
            return authenticate()

    init_db(foo.config['database_uri'])

    if 'key_file' in foo.config and 'cert_file' in foo.config:
        import ssl
        verification = ssl.CERT_NONE
        ca_certs = None
        if 'ca_cert' in foo.config:
            ca_certs = [foo.config['ca_cert']]
            verification = ssl.CERT_OPTIONAL
        http_server = WSGIServer(
            (foo.config['bind_address'], int(foo.config['bind_port'])),
            foo,
            keyfile=foo.config['key_file'],
            certfile=foo.config['cert_file'],
            cert_reqs=verification,
            ca_certs=ca_certs)
    else:
        http_server = WSGIServer((foo.config['bind_address'],
                                  int(foo.config['bind_port'])), foo)
    http_server.serve_forever()
