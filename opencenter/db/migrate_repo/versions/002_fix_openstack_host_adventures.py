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

import json
import os

from sqlalchemy import *
from migrate import *

from opencenter.db.api import api_from_models


adventures = [
    {'name': 'Disable Scheduling on this Host',
     'dsl': 'openstack_disable_host.json',
     'criteria': {'001': 'openstack_disable_host.criteria',
                  '002': '002_openstack_disable_host.criteria'}},
    {'name': 'Enable Scheduling on this Host',
     'dsl': 'openstack_enable_host.json',
     'criteria': {'001': 'openstack_enable_host.criteria',
                  '002': '002_openstack_enable_host.criteria'}}]


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    api = api_from_models()
    for adventure in adventures:
        db_entries = api._model_query('adventures',
                                      'name="%s"' % adventure['name'])

        if len(db_entries) == 1:
            db_entry = db_entries[0]
            criteria_path = os.path.join(
                os.path.dirname(__file__), adventure['criteria']['002'])
            db_entry['criteria'] = open(criteria_path).read()

            api.adventure_update_by_id(db_entry['id'], db_entry)


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    api = api_from_models()
    for adventure in adventures:
        db_entries = api._model_query('adventures',
                                      'name="%s"' % adventure['name'])

        if len(db_entries) == 1:
            db_entry = db_entries[0]
            criteria_path = os.path.join(
                os.path.dirname(__file__), adventure['criteria']['001'])
            db_entry['criteria'] = open(criteria_path).read()

            api.adventure_update_by_id(db_entry['id'], db_entry)
