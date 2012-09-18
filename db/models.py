import json

from sqlalchemy import (Column, Integer, String, ForeignKey,
                        Text, Enum, DateTime)
from sqlalchemy.orm import relationship, backref
import sqlalchemy.types as types

from database import Base


# Special Fields
class JsonBlob(types.TypeDecorator):

    impl = types.Text

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


class Nodes(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64), unique=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    clusters = relationship('Clusters',
                            backref=backref('nodes',
                            uselist=False,
                            lazy='dynamic'))
    type_id = Column(Integer, ForeignKey('types.id'))
    types = relationship('Types',
                         backref=backref('nodes',
                         uselist=False,
                         lazy='dynamic'))
    type_state = Column(Integer, ForeignKey('typestates.id'))
    config = Column(JsonBlob)

    def __init__(self, hostname, role_id=None, cluster_id=None, config=None,
                 type_id=None, typestate=None):
        self.hostname = hostname
        self.type_id = type_id
        self.role_id = role_id
        self.cluster_id = cluster_id
        self.config = config
        self.typestate = typestate

    def __repr__(self):
        return '<Nodes %r>' % (self.hostname)


class Types(Base):
    __tablename__ = 'types'
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Types %r>' % (self.name)


class TypeStates(Base):
    __tablename__ = 'typestates'
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True)
    type_id = Column(Integer, ForeignKey('types.id'))
    types = relationship('Types',
                         backref=backref('states',
                         uselist=False,
                         lazy='dynamic'))

    def __init__(self, name, type_id):
        self.name = name
        self.type_id = type_id

    def __repr__(self):
        return '<TypeStates %r>' % (self.name)


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
    # config = Column(Text)
    config = Column(JsonBlob)
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
    payload = Column(JsonBlob)
    state = Column(Enum('pending', 'running', 'done', 'timeout', 'cancelled'))
    result = Column(JsonBlob)
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
        self.submitted = submitted
        self.completed = completed
        self.expires = expires

    def __repr__(self):
        return '<Clusters %r>' % (self.name)
