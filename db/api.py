# vim: tabstop=4 shiftwidth=4 softtabstop=4

from itertools import islice
import json

from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.sql import and_, or_

from db.database import db_session
from db import exceptions as exc
from db.models import Adventures, Clusters, Nodes, Roles, Tasks


def _model_get_all(model):
    tables = {'adventures': Adventures,
              'clusters': Clusters,
              'nodes': Nodes,
              'roles': Roles,
              'tasks': Tasks}
    result = [dict((c, getattr(r, c))
              for c in r.__table__.columns.keys())
              for r in tables[model].query.all()]
    return result


def _model_get_columns(model):
    tables = {'adventures': Adventures,
              'clusters': Clusters,
              'nodes': Nodes,
              'roles': Roles,
              'tasks': Tasks}
    result = [c for c in tables[model].__table__.columns.keys()]
    return result


def _model_get_schema(model):
    obj = globals()[model.capitalize()]
    cols = obj.__table__.columns

    fields = {}
    for k in cols.keys():
        fields[k] = {}
        fields[k]['type'] = str(cols[k].type)
        if repr(cols[k].type) == 'JsonBlob()':
            fields[k]['type'] = 'JSON'

        fields[k]['unique'] = cols[k].unique or cols[k].primary_key

        if len(cols[k].foreign_keys) > 0:
            fields[k]['fk'] = list(cols[k].foreign_keys)[0].target_fullname

    return {'schema': fields}


def _model_delete_by_id(model, pk_id):
    """Query helper for deleting a node

    :param model: name of the table model
    :param pk_id: id to delete
    """
    tables = {'adventures': Adventures,
              'clusters': Clusters,
              'nodes': Nodes,
              'roles': Roles,
              'tasks': Tasks}
    r = tables[model].query.filter_by(id=pk_id).first()
    try:
        db_session.delete(r)
        db_session.commit()
        return True
    except UnmappedInstanceError, e:
        db_session.rollback()
        msg = "%s id does not exist" % (model.title())
        raise exc.IdNotFound(message=msg)
    except InvalidRequestError, e:
        db_session.rollback()
        msg = e.msg
        raise Foo(msg)


def _model_get_by_id(model, pk_id):
    """Query helper for getting a node

    :param model: name of the table model
    :param pk_id: id to delete
    """
    tables = {'adventures': Adventures,
              'clusters': Clusters,
              'nodes': Nodes,
              'roles': Roles,
              'tasks': Tasks}
    r = tables[model].query.filter_by(id=pk_id).first()

    if not r:
        return None

    result = [dict((c, getattr(r, c))
                   for c in r.__table__.columns.keys())
              for r in tables[model].query.all()]

    return result[0]


def _model_get_by_filter(model, filters):
    """Query helper that returns a node dict.

    :param filters: dictionary of filters; that are combined with AND
                    to filter the result set.
    """
    tables = {'adventures': Adventures,
              'clusters': Clusters,
              'nodes': Nodes,
              'roles': Roles,
              'tasks': Tasks}
    filter_options = and_(
        * [tables[model].__table__.columns[k] == v
           for k, v in filters.iteritems()])
    r = tables[model].query.filter(filter_options).first()
    if not r:
        result = None
    else:
        result = dict((c, getattr(r, c))
                      for c in r.__table__.columns.keys())
    return result


def _model_update_by_id(model, pk_id, fields):
    """Query helper for updating a row

    :param model: name of the table model
    :param pk_id: id to update
    :param pk_id: dict of columns:values to update
    """
    tables = {'adventures': Adventures,
              'clusters': Clusters,
              'nodes': Nodes,
              'roles': Roles,
              'tasks': Tasks}
    field_list = [c for c in tables[model].__table__.columns.keys()]
    field_list.remove('id')
    r = tables[model].query.filter_by(id=pk_id).first()
    for field in field_list:
        if field in fields:
            r.__setattr__(field, fields[field])
    try:
        db_session.commit()
        return dict((c, getattr(r, c))
                    for c in r.__table__.columns.keys())
    except Exception, e:
        db_session.rollback()


def adventures_get_all():
    """Query helper that returns a dict of all adventures"""
    return _model_get_all('adventures')


def adventures_get_by_node_id(node_id):
    """Query helper that returns a dict of all the adventures
       for a given node_id

    :param node_id: blah blah
    """
    # this is the SQL query we are trying to achieve
    # select adventures.* from adventures join nodes on
    #    (nodes.backend = adventures.backend or adventures.backend = null)
    #    AND (nodes.backend_state = adventures.backend_state
    #         OR adventures.backend_state is null);

    stmt1 = or_(Adventures.backend == Nodes.backend,
                Adventures.backend == 'null')
    stmt2 = or_(Adventures.backend_state == Nodes.backend_state,
                Adventures.backend_state == 'null')
    adventure_list = Adventures.query.join(
        Nodes,
        and_(stmt1, stmt2, Nodes.id == node_id)).all()

    result = list()
    for r in adventure_list:
        tmp = dict()
        for c in r.__table__.columns.keys():
            if c == 'dsl':
                if r.__getattribute__('language') == 'json':
                    tmp[c] = json.loads(getattr(r, c))
                else:
                    tmp[c] = getattr(r, c)
            else:
                tmp[c] = getattr(r, c)
        result.append(tmp)
    return result


def adventure_create(fields):
    field_list = [c for c in Adventures.__table__.columns.keys()]
    field_list.remove('id')
    a = Adventures(**dict((field, fields[field])
                          for field in field_list if field in fields))
    db_session.add(a)
    try:
        db_session.commit()
        return dict((c, getattr(a, c))
                    for c in a.__table__.columns.keys())
    except IntegrityError, e:
        db_session.rollback()
        msg = "Unable to create Adventure"
        raise exc.CreateError(message=msg)


def adventure_delete_by_id(adventure_id):
    """Query helper for deleting a adventure

    :param adventure_id: id of adventure to delete
    """
    try:
        return _model_delete_by_id('adventures', adventure_id)
    except exc.IdNotFound, e:
        raise exc.AdventureNotFound(e.message)


def adventure_get_by_filter(filters):
    """Query helper that returns a adventure dict.

    :param filters: dictionary of filters; that are combined with AND
                    to filter the result set.
    """
    #TODO(shep): this should accept an array.. and return the first result
    result = _model_get_by_filter('adventures', filters)
    return result


def adventure_get_by_id(adventure_id):
    """Query helper that returns an adventure by adventure_id

    :param adventure_id: id of the adventure to lookup
    """
    result = adventure_get_by_filter({'id': adventure_id})
    return result


def adventure_get_columns():
    """Query helper that returns a list of Adventure columns"""
    result = _model_get_columns('adventures')
    return result


def adventure_update_by_id(node_id, fields):
    """Query helper that updates an adventure by adventure_id

    :param adventure_id: id of the adventure to lookup
    :param fields: dict of column:value to update
    """
    result = _model_update_by_id('adventures', node_id, fields)
    return result


def clusters_get_all():
    """Query helper that returns a dict of all clusters"""
    return _model_get_all('clusters')


def cluster_get_by_filter(filters):
    """Query helper that returns a cluster dict.

    :param filters: dictionary of filters; that are combined with AND
                    to filter the result set.
    """
    #TODO(shep): this should accept an array.. and return the first result
    result = _model_get_by_filter('clusters', filters)
    return result


def cluster_get_by_id(cluster_id):
    """Query helper that returns a node by cluster_id

    :param cluster_id: id of the cluster to lookup
    """
    result = cluster_get_by_filter({'id': cluster_id})
    return result


def cluster_get_columns():
    """Query helper that returns a list of Clusters columns"""
    result = _model_get_columns('clusters')
    return result


def cluster_delete_by_id(cluster_id):
    """Query helper for deleting a cluster

    :param cluster_id: id of cluster to delete
    """
    try:
        return _model_delete_by_id('clusters', cluster_id)
    except exc.IdNotFound, e:
        raise exc.NodeNotFound()


def node_create(fields):
    field_list = [c for c in Nodes.__table__.columns.keys()]
    field_list.remove('id')
    a = Nodes(**dict((field, fields[field])
                     for field in field_list if field in fields))
    db_session.add(a)
    try:
        db_session.commit()
        return dict((c, getattr(a, c))
                    for c in a.__table__.columns.keys())
    except IntegrityError, e:
        db_session.rollback()
        msg = "Unable to create Node, duplicate entry"
        raise exc.CreateError(message=msg)


def node_update_by_id(node_id, fields):
    result = _model_update_by_id('nodes', node_id, fields)
    return result


def nodes_get_all():
    """Query helper that returns a dict of all nodes"""
    return _model_get_all('nodes')


def node_get_columns():
    """Query helper that returns a list of Nodes columns"""
    result = _model_get_columns('nodes')
    return result


def node_get_by_filter(filters):
    """Query helper that returns a node dict.

    :param filters: dictionary of filters; that are combined with AND
                    to filter the result set.
    """
    #TODO(shep): this should accept an array.. and return the first result
    result = _model_get_by_filter('nodes', filters)
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
    try:
        return _model_delete_by_id('nodes', node_id)
    except exc.IdNotFound, e:
        raise exc.NodeNotFound()


def roles_get_all():
    """Query helper that returns a dict of all roles"""
    return _model_gett_all('roles')


def role_get_columns():
    """Query helper that returns a list of Roles columns"""
    result = _model_get_columns('roles')
    return result


def task_get_columns():
    """Query helper that returns a list of Tasks columns"""
    result = _model_get_columns('tasks')
    return result


def task_update_by_id(task_id, fields):
    """Query helper that updates an task by task_id

    :param task_id: id of the task to lookup
    :param fields: dict of column:value to update
    """
    result = _model_update_by_id('tasks', task_id, fields)
    return result

def tasks_get_all():
    """Query helper that returns a dict of all tasks"""
    return _model_get_all('tasks')


def task_get_columns():
    """Query helper that returns a list of Tasks columns"""
    return _model_get_columns('tasks')


def task_get_by_filter(filters):
    """Query helper that returns a task dict.

    :param filters: dictionary of filters; that are combined with AND
                    to filter the result set.
    """
    #TODO(shep): should this accept an array.. and return the first result?
    return _model_get_by_filter('tasks', filters)


def task_get_by_id(task_id):
    """Query helper that returns a task by task_id

    :param task_id: id of the task to lookup
    """
    return task_get_by_filter({'id': task_id})
