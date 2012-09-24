from sqlalchemy import *
from migrate import *

from migrate.changeset import schema

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, object_mapper

from db.models import Nodes, Roles, Tasks, Clusters, Types, TypeStates

# Base = declarative_base()
meta = MetaData()


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    types = Table('types', meta, autoload=True)
    types.insert().values(name='Unprovisioned').execute()


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    types = Table('types', meta, autoload=True)
    types.delete().where(types.c.name == 'Unprovisioned').execute()
