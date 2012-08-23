from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base


class Nodes(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64), unique=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
#    role_name = relationship('Roles',
#        backref=backref('name', lazy='dynamic'))
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
#    cluster_name = relationship('Clusters',
#        backref=backref('name', lazy='dynamic'))

    def __init__(self, hostname=None, role_id=None, cluster_id=None):
        self.hostname = hostname
        self.role_id = role_id
        self.cluster_id = cluster_id

    def __repr__(self):
        return '<Nodes %r>' % (self.hostname)


class Roles(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    description = Column(String(80))

    def __init(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Roles %r>' % role.name


class Clusters(Base):
    __tablename__ = 'clusters'
    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    description = Column(String(80))

    def __init(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Clusters %r>' % role.name
