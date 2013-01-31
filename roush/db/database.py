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

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.ext.declarative import declarative_base

# engine = create_engine('sqlite:///roush.db', convert_unicode=True)
engine = None
session = scoped_session(lambda: create_session(autocommit=False,
                                                autoflush=False,
                                                bind=engine))
Base = declarative_base()
Base.query = session.query_property()


def init_db(uri, **kwargs):
    global engine
    engine = create_engine(uri, **kwargs)
    Base.metadata.create_all(bind=engine)
