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
    # Create default nodes
    workspace = api.node_create({'name': 'workspace'})
    unprov = api.node_create({'name': 'unprovisioned'})
    api._model_create('facts', {'node_id': unprov['id'],
                                'key': 'parent_id',
                                'value': workspace['id']})
    support = api.node_create({'name': 'support'})
    api._model_create('facts', {'node_id': support['id'],
                                'key': 'parent_id',
                                'value': workspace['id']})

    # Add default fact to the default nodes
    node_id_list = [workspace['id'], unprov['id'], support['id']]
    for nid in node_id_list:
        api.fact_create({'node_id': nid,
                         'key': 'backends',
                         'value': ["container", "node"]})


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    node_list = ['"support"', '"unprovisioned"', '"workspace"']
    api = api_from_models()
    for node in node_list:
        tmp = api.nodes_query('name = %s' % node)
        fact_list = api.facts_query('node_id = %s' % tmp['id'])
        for fact in fact_list:
            api.fact_delete_by_id(fact['id'])
        api.node_delete_by_id(tmp['id'])
