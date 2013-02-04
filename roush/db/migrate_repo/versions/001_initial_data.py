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

from roush.db.models import Adventures, Nodes, Tasks
from roush.db.api import api_from_models


# Base = declarative_base()
api = api_from_models()
meta = MetaData()


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    adventures = [
        {'name': 'install chef client',
         'dsl': 'install_chef.json',
         'criteria': 'install_chef.criteria',
         'args': 'install_chef.args'},
        {'name': 'run chef',
         'dsl': 'run_chef.json',
         'criteria': 'run_chef.criteria',
         'args': 'run_chef.args'},
        {'name': 'install chef server',
         'dsl':  'install_chef_server.json',
         'criteria': 'install_chef_server.criteria',
         'args': 'install_chef_server.args'},
        {'name': 'create nova cluster',
         'dsl': 'create_nova_cluster.json',
         'criteria': 'create_nova_cluster.criteria',
         'args': 'create_nova_cluster.args'},
        {'name': 'install nova controller',
         'dsl': 'install_nova_controller.json',
         'criteria': 'install_nova_controller.criteria',
         'args': 'install_nova_controller.args'},
        {'name': 'install nova compute',
         'dsl': 'install_nova_compute.json',
         'criteria': 'install_nova_compute.criteria',
         'args': 'install_nova_compute.args'},
        {'name': 'download chef cookbooks',
         'dsl': 'download_cookbooks.json',
         'criteria': 'download_cookbooks.criteria',
         'args': 'download_cookbooks.args'},
        {'name': 'sleep',
         'dsl': 'sleep.json',
         'criteria': 'sleep.criteria',
         'args': 'sleep.args'}]

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

    canned_filters = [{'name': 'unprovisioned nodes',
                       'filter_type': 'node',
                       'expr': 'backend=\'unprovisioned\''},
                      {'name': 'chef client nodes',
                       'filter_type': 'node',
                       'expr': 'backend=\'chef-client\''},
                      {'name': 'chef-server',
                       'filter_type': 'interface',
                       'expr': 'facts.chef_server_uri != None and '
                               'facts.chef_server_pem != None'}]

    for new_filter in canned_filters:
        api._model_create('filters', new_filter)


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    types = Table('types', meta, autoload=True)
    types.delete().where(types.c.name == 'Unprovisioned').execute()
