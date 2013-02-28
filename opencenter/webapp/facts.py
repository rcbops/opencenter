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

import flask

from opencenter.db.api import api_from_models
from opencenter.webapp import generic


object_type = 'facts'
singular_object_type = generic.singularize(object_type)

bp = flask.Blueprint(object_type, __name__)


@bp.route('/', methods=['GET'])
def list():
    return generic.list(object_type)


@bp.route('/', methods=['POST'])
def create():
    old_fact = None

    # if we are creating with the same host_id and key, then we'll just update
    # fields = api._model_get_columns(object_type)

    api = api_from_models()
    data = flask.request.json

    model_object = None

    if 'node_id' in data and 'key' in data:
        old_fact = api._model_get_first_by_query(
            object_type, 'node_id=%d and key="%s"' % (int(data['node_id']),
                                                      data['key']))

    if old_fact:
        model_object = api._model_update_by_id(
            object_type, old_fact['id'], data)
        # send update notification
        generic._notify(model_object, object_type, old_fact['id'])
    else:
        try:
            model_object = api._model_create(object_type, data)
        except KeyError as e:
            # missing required field
            return generic.http_badrequest(msg=str(e))

        generic._notify(model_object, object_type, model_object['id'])

    href = flask.request.base_url + str(model_object['id'])
    return generic.http_response(201, '%s Created' %
                                 singular_object_type.capitalize(), ref=href,
                                 **{singular_object_type: model_object})


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)
