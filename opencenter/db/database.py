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

import os

from migrate.versioning import api as migrate_api
from migrate.versioning import repository as repo
from migrate.exceptions import DatabaseNotControlledError
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.ext.declarative import declarative_base

from opencenter.db import migrate_repo as roush_repo

# engine = create_engine('sqlite:///opencenter.db', convert_unicode=True)
engine = None
session = scoped_session(lambda: create_session(autocommit=False,
                                                autoflush=False,
                                                bind=engine))
Base = declarative_base()
Base.query = session.query_property()


def init_db(uri, migrate=True, **kwargs):
    global engine
    engine = create_engine(uri, **kwargs)
    Base.metadata.create_all(bind=engine)

    if migrate:
        migrate_db(engine, **kwargs)


def _memorydb_migrate_db(**kwargs):
    """
    This is crazy crackheaded, and abusive to sqlalchemy.

    We'll take out dispose so the migrate stuff doesn't kill it,
    and push through the migrate.  This makes a bunch of assumptions
    that are likely stupid, but since this is done on a memory-backed
    db for testing, it's probably okay.

    Just don't run this on a real db.
    """
    def dispose_patch(*args, **kwargs):
        pass

    global engine
    old_dispose = engine.dispose
    engine.dispose = dispose_patch

    repo_path = repo.Repository(
        os.path.abspath(os.path.dirname(opencenter_repo.__file__)))
    migrate_api.version_control(engine, repo_path)
    migrate_api.upgrade(engine, repo_path)
    engine.dispose = old_dispose


def migrate_db(uri, **kwargs):
    # Need to apply migrate-versions
    repo_path = repo.Repository(
        os.path.abspath(os.path.dirname(opencenter_repo.__file__)))
    try:
        db_ver = migrate_api.db_version(uri, repo_path)
    except DatabaseNotControlledError:
        migrate_api.version_control(uri, repo_path)
        db_ver = migrate_api.db_version(uri, repo_path)
    # Find the current version in the repo
    latest = migrate_api.version(str(repo_path))

    if db_ver < latest:
        migrate_api.upgrade(uri, repo_path)
