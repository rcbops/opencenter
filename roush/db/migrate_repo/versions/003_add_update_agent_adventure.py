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
meta = MetaData()


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    adventures = [
        {'name': 'update roush agent',
         'dsl': 'update_agent.json',
         'criteria': 'update_agent.criteria',
         'args': 'update_agent.args'}]

    api = api_from_models()
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
    pass
