import json

from sqlalchemy import *
from migrate import *

from migrate.changeset import schema

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, object_mapper

from db.models import Adventures, Nodes, Roles, Tasks, Clusters
from db import api as api


# Base = declarative_base()
meta = MetaData()


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    adventures = [
        {'name': 'install chef',
         'dsl': json.dumps(
                {'start_state': 's1',
                 'states': {
                        's1': {'action': 'run_task',
                               'parameters': {'action': 'install_chef'},
                               'on_success': 's2' }
                        's2': {'action': 'set_backend',
                               'parameters': {'backend': 'chef-client',
                                              'backend_state': 'installed'}}}}),
         'language': 'json',
         'backend': 'unprovisioned',
         'backend_state': 'unknown'},
        {'name': 'run chef',
         'dsl': json.dumps(
                {'start_state': 's1',
                 'states': {
                        's1': {'action': 'run_task',
                               'parameters': {'action': 'run_chef'}}}}),
         'language': 'json',
         'backend': 'chef-client',
         'backend_state': 'installed'},
        {'name': 'install chef server',
         'dsl':  json.dumps(
                {'start_state': 's1',
                 'states': {
                        's1': {'action': 'run_task',
                               'parameters': {'action': 'install_chef_server'},
                               'on_success': 's2'},
                        's2': {'action': 'set_backend',
                               'parameters': {'backend': 'chef-server',
                                              'backend_state': 'installed'}}}}),
         'language': 'json',
         'backend': 'unprovisioned',
         'backend_state': 'unknown'}]

    for adventure in adventures:
        adv = api.adventure_create(adventure)


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    types = Table('types', meta, autoload=True)
    types.delete().where(types.c.name == 'Unprovisioned').execute()
