from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship, backref
from database import Base


class Nodes(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64), unique=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    extra = Column(Text)

    def __init__(self, hostname=None, role_id=None, cluster_id=None, extra=None):
        self.hostname = hostname
        self.role_id = role_id
        self.cluster_id = cluster_id
        self.extra = extra

    def __repr__(self):
        return '<Nodes %r>' % (self.hostname)


class Roles(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    description = Column(String(80))
    node = relationship('Nodes',
        backref=backref('role', uselist=False, lazy='dynamic'))

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
    extra = Column(Text)
    node = relationship('Nodes',
        backref=backref('cluster', uselist=False, lazy='dynamic'))

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Clusters %r>' % (self.name)
