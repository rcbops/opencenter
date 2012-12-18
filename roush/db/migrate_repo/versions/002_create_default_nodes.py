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
    workspace = api.node_create({'name': 'workspace'})
    unprov = api.node_create({'name': 'unprovisioned',
                              'parent_id': workspace['id']})
    support = api.node_create({'name': 'support',
                               'parent_id': workspace['id']})


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    node_list = ['"support"', '"unprovisioned"', '"workspace"']
    for node in node_list:
        tmp = api.node_query('name = %s' % node)
        api.node_delete_by_id(tmp['id'])
