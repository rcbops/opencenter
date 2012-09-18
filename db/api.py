# vim: tabstop=4 shiftwidth=4 softtabstop=4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.sql import and_, or_

from db.database import db_session
from db import exceptions as exc
from db.models import Nodes, Roles, Clusters, Tasks


def nodes_get_all():
    """Query helper that returns all nodes"""
    result = [dict((c, getattr(r, c))
              for c in r.__table__.columns.keys())
              for r in Nodes.query.all()]
    return result


def node_get_by_filter(filters):
    """Query helper that returns a node dict.

    :param filters: dictionary of filters; that are combined with AND
                    to filter the result set.
    """
    filter_options = and_(
        * [Nodes.__table__.columns[k] == v
           for k, v in filters.iteritems()])
    r = Nodes.query.filter(filter_options).first()
    if not r:
        result = None
    else:
        result = dict((c, getattr(r, c))
                      for c in r.__table__.columns.keys())
    return result


def node_get_by_id(node_id):
    """Query helper that returns a node by node_id

    :param node_id: id of the node to lookup
    """
    result = node_get_by_filter({'id': node_id})
    return result


def node_delete_by_id(node_id):
    """Query helper for deleting a node

    :param node_id: id of node to delete
    """
    r = Nodes.query.filter_by(id=node_id).first()
    try:
        db_session.delete(r)
        db_session.commit()
        return True
    except UnmappedInstanceError, e:
        db_session.rollback()
        raise exc.NodeNotFound()


def task_get_by_filter(filters):
    """Query helper that returns a node dict.

    :param filters: dictionary of filters; that are combined with AND
                    to filter the result set.
    """
    filter_options = and_(
        * [Tasks.__table__.columns[k] == v
           for k, v in filters.iteritems()])
    r = Tasks.query.filter(filter_options).first()
    if not r:
        result = None
    else:
        result = dict((c, getattr(r, c))
                      for c in r.__table__.columns.keys())
    return result
