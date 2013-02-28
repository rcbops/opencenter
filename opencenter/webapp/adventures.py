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
from opencenter.db import exceptions
from opencenter.webapp import generic
# from opencenter.webapp import solver
# from opencenter.webapp import utility


object_type = 'adventures'
bp = flask.Blueprint(object_type, __name__)


@bp.route('/', methods=['GET', 'POST'])
def list():
    return generic.list(object_type)


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)


@bp.route('/<adventure_id>/execute', methods=['POST'])
def execute_adventure(adventure_id):
    data = flask.request.json

    if not 'node' in data:
        return generic.http_badrequest(msg='node not specified')

    api = api_from_models()
    try:
        adventure = api._model_get_by_id('adventures', int(adventure_id))
    except exceptions.IdNotFound:
        message = 'Not Found: Adventure %s' % adventure_id
        return generic.http_notfound(msg=message)

    try:
        return generic.http_solver_request(data['node'], [],
                                           api=api, plan=adventure['dsl'])
    except exceptions.IdNotFound:
        #Can IdNotFound be raised for any other reason?
        return generic.http_notfound(msg='Not Found: Node %s' % data['node'])
