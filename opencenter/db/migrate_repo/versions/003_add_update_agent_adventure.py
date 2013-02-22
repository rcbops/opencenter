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

import json
import os

from sqlalchemy import *
from migrate import *

from migrate.changeset import schema

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, object_mapper

from opencenter.db.models import Adventures, Nodes, Tasks
from opencenter.db.api import api_from_models


# Base = declarative_base()
meta = MetaData()


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    api = api_from_models()
    workspace = api.nodes_query('name = "workspace"')
    api.attr_create({'node_id': workspace[0]['id'],
                     'key': 'json_schema_version',
                     'value': 1})

    adventures = [
        {'name': 'update agent',
         'dsl': 'update_agent.json',
         'criteria': 'update_agent.criteria',
         'args': 'update_agent.args'},
        {'name': 'restart agent',
         'dsl': 'restart_agent.json',
         'criteria': 'restart_agent.criteria',
         'args': 'restart_agent.args'},
        {'name': 'Create Availability Zone',
         'dsl': 'create_az.json',
         'criteria': 'create_az.criteria',
         'args': 'create_az.args'},
        {'name': 'Disable Scheduling on this Host',
         'dsl': 'openstack_disable_host.json',
         'criteria': 'openstack_disable_host.criteria',
         'args': 'openstack_disable_host.args'},
        {'name': 'Enable Scheduling on this Host',
         'dsl': 'openstack_enable_host.json',
         'criteria': 'openstack_enable_host.criteria',
         'args': 'openstack_enable_host.args'},
        {'name': 'Evacuate Host',
         'dsl': 'openstack_evacuate_host.json',
         'criteria': 'openstack_evacuate_host.criteria',
         'args': 'openstack_evacuate_host.args'},
        {'name': 'Upload Initial Glance Images',
         'dsl': 'openstack_evacuate_host.json',
         'criteria': 'openstack_evacuate_host.criteria',
         'args': 'openstack_evacuate_host.args'}]

    for adventure in adventures:
        json_path = os.path.join(
            os.path.dirname(__file__), adventure['dsl'])
        criteria_path = os.path.join(
            os.path.dirname(__file__), adventure['criteria'])
        args_path = os.path.join(
            os.path.dirname(__file__), adventure['args'])

        adventure['dsl'] = json.loads(open(json_path).read())
        adventure['criteria'] = open(criteria_path).read()
        adventure['args'] = json.loads(open(args_path).read())
        adv = api.adventure_create(adventure)


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    api = api_from_models()
    adv = api.adventures_query('name = "update agent"')
    rc = api.adventure_delete_by_id(adv['id'])
