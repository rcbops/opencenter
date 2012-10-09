import json
from time import time

from sqlalchemy import (Column, Integer, String, ForeignKey,
                        Text, Enum, DateTime)
from sqlalchemy.orm import relationship, backref
import sqlalchemy.types as types
from sqlalchemy.exc import InvalidRequestError

from database import Base


# Special Fields
class JsonBlob(types.TypeDecorator):

    impl = types.Text

    def _is_valid_obj(self, value):
        if isinstance(value, dict) or isinstance(value, list):
            return True
        else:
            return False

    def process_bind_param(self, value, dialect):
        if self._is_valid_obj(value):
            return json.dumps(value)
        else:
            raise InvalidRequestError("%s is not an accepted type" %
                                      type(value))

    def process_result_value(self, value, dialect):
        if value is None:
            value = '{}'
        return json.loads(value)


class Nodes(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64), unique=True, nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'))
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    clusters = relationship('Clusters',
                            backref=backref('nodes',
                            lazy='dynamic'))
    backend = Column(String(30))  # Adventures.backend
    backend_state = Column(String(30))  # Adventures.backend_state
    config = Column(JsonBlob, default={})

    def __init__(self, hostname, role_id=None, cluster_id=None, config=None,
                 backend=None, backend_state=None):
        self.hostname = hostname
        self.role_id = role_id
        self.cluster_id = cluster_id
        self.config = config
        self.backend = backend
        self.backend_state = backend_state

    def __repr__(self):
        return '<Nodes %r>' % (self.hostname)


class Adventures(Base):
    __tablename__ = 'adventures'
    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    dsl = Column(JsonBlob, default={})
    criteria = Column(String(255))

    def __init__(self, name, dsl, criteria='1 = 1'):
        self.name = name
        self.dsl = dsl
        self.criteria = criteria

    def __repr__(self):
        return '<Adventures %r>' % (self.name)


class Roles(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    description = Column(String(80))
    node = relationship('Nodes', backref=backref('role',
                                                 uselist=False,
                                                 lazy='dynamic'))

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Roles %r>' % (self.name)


class Clusters(Base):
    __tablename__ = 'clusters'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    description = Column(String(80))
    config = Column(JsonBlob, default={})
    node = relationship('Nodes', backref=backref('cluster',
                                                 uselist=False,
                                                 lazy='dynamic'))

    def __init__(self, name, description, config=None):
        self.name = name
        self.description = description
        self.config = config

    def __repr__(self):
        return '<Clusters %r>' % (self.name)


class Tasks(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey('nodes.id'))
    action = Column(String(40))
    payload = Column(JsonBlob, default={})
    state = Column(
        Enum('pending', 'running', 'done', 'timeout', 'cancelled'),
        default='pending')
    result = Column(JsonBlob, default={})
    submitted = Column(Integer)
    completed = Column(Integer)
    expires = Column(Integer)
    node = relationship('Nodes', backref=backref('tasks',
                                                 uselist=False,
                                                 lazy='dynamic'))

    def __init__(self, node_id, action, payload, state,
                 result=None, submitted=None, completed=None,
                 expires=None):
        self.node_id = node_id
        self.action = action
        self.payload = payload
        self.state = state
        self.result = result
        self.submitted = int(time())
        self.completed = completed
        self.expires = expires

    def __repr__(self):
        return '<Clusters %r>' % (self.name)
