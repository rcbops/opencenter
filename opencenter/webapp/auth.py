#!/usr/bin/env python
#               OpenCenter™ is Copyright 2013 by Rackspace US, Inc.
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

from functools import wraps

from flask import request, Response, current_app


def check_auth(username, password, roles):
    valid_user = current_app.config.get('admin_user')
    valid_pass = current_app.config.get('admin_pass')
    if valid_user is None and valid_pass is None:
        return True  # no auth
    user_roles = get_roles(username)
    if username == valid_user and valid_pass == password and (
            'admin' in user_roles or roles is None or any(
                [r in roles for r in user_roles])):
        return True  # good auth
    return False


def authenticate():
    return Response(
        '{"msg": "unauthorized"}', 401,
        {})


def get_roles(username):
    return ['admin']


def is_allowed(roles=None):
    c = current_app.config
    if 'admin_user' in c and 'admin_pass' in c:
        auth = request.authorization
        if not auth or not check_auth(auth.username,
                                      auth.password,
                                      roles):
            return False
    return True


class requires_auth(object):
    def __init__(self, roles=None):
        self.roles = roles

    def __call__(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not is_allowed(self.roles):
                return authenticate()
            return f(*args, **kwargs)
        return decorated
