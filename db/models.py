from sqlalchemy import (Column, Integer, String, ForeignKey,
                        Text, Enum, DateTime)
from sqlalchemy.orm import relationship, backref
from database import Base


class Nodes(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64), unique=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    config = Column(Text)

    def __init__(self, hostname=None, role_id=None,
                 cluster_id=None, config=None):
        self.hostname = hostname
        self.role_id = role_id
        self.cluster_id = cluster_id
        self.config = config

    def __repr__(self):
        return '<Nodes %r>' % (self.hostname)


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
    config = Column(Text)
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
    payload = Column(Text)
    state = Column(Enum('pending', 'running', 'done', 'timeout', 'cancelled'))
    result = Column(Text)
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
