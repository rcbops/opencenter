#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

import sys
import pkg_resources


def replace_dist(requirement):
    try:
        return pkg_resources.require(requirement).pop()
    except pkg_resources.VersionConflict as e:
        dist = e.args[0]
        req = e.args[1]
        if dist.key == req.key and not dist.location.endswith('.egg'):
            del pkg_resources.working_set.by_key[dist.key]
            # We assume there is no need to adjust sys.path
            # and the associated pkg_resources.working_set.entries
            return pkg_resources.require(requirement).pop()

dist = replace_dist("SQLAlchemy >= 0.6.3")
sys.path = [dist.location] + sys.path

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
