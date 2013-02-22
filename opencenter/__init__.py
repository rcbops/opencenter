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

from opencenter.db.database import init_db
from opencenter.webapp import WebServer
from opencenter.webapp.auth import is_allowed, authenticate


def main():
    server = WebServer("opencenter",
                       argv=sys.argv[1:],
                       configfile='local.conf',
                       debug=True)

    @server.after_request
    def allow_cors(response):
        if 'cors_uri' in server.config and \
                'Origin' in request.headers and \
                request.headers['Origin'] in server.config['cors_uri']:
            response.headers['Access-Control-Allow-Origin'] = \
                request.headers['Origin']
            response.headers['Access-Control-Allow-Methods'] = \
                'HEAD,GET,PUT,POST,OPTIONS,DELETE'
            response.headers['Access-Control-Allow-Headers'] = \
                'Content-Type'
        return response

    @server.before_request
    def auth_f():
        if not is_allowed(roles=None):
            return authenticate()

    init_db(server.config['database_uri'])

    if 'key_file' in server.config and 'cert_file' in server.config:
        import ssl
        verification = ssl.CERT_NONE
        ca_certs = None
        if 'ca_cert' in server.config:
            ca_certs = [server.config['ca_cert']]
            verification = ssl.CERT_OPTIONAL
        http_server = WSGIServer(
            (server.config['bind_address'], int(server.config['bind_port'])),
            server,
            keyfile=server.config['key_file'],
            certfile=server.config['cert_file'],
            cert_reqs=verification,
            ca_certs=ca_certs)
    else:
        http_server = WSGIServer((server.config['bind_address'],
                                  int(server.config['bind_port'])), server)
    http_server.serve_forever()
