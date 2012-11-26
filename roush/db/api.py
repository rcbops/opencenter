# vim: tabstop=4 shiftwidth=4 softtabstop=4
# tab stops are 8.  ^^ this is wrong

import logging
from functools import partial

import sqlalchemy

from roush import backends
from roush.db import models
from roush.db import abstraction
from roush.db import inmemory

LOG = logging.getLogger(__name__)

model_list = {}
in_memory_dict = {}


backends.load()

for d in dir(models):
    model_name = d.lower()
    model = getattr(models, d)

    if type(models.Nodes) == type(getattr(models, d)) and d != 'Base':
        model_list[model_name] = abstraction.SqlAlchemyAbstraction(
            model, model_name)
    elif isinstance(getattr(models,d), type) and \
            issubclass(model, inmemory.InMemoryBase) and \
            d != 'Primitives':
        in_memory_dict[model_name] = {}

        model_list[model_name] = abstraction.InMemoryAbstraction(
            model, d, in_memory_dict[model_name])
    elif d == 'Primitives':
        # these run off the backend.backend_primitives dict.
        model_list[model_name] = abstraction.InMemoryAbstraction(
            model, d, backends.backend_primitives)


def _get_models():
    return model_list.keys()


def _call_model(function, model, *args, **kwargs):
    model = model.lower()

    if not model in model_list:
        raise KeyError('unknown model %s' % model)

    if not hasattr(model_list[model], function):
        raise ValueError('unknown model function %s' % function)

    return getattr(model_list[model], function)(*args, **kwargs)


for name, method in {'_model_get_all': 'get_all',
                     '_model_get_columns': 'get_columns',
                     '_model_get_schema': 'get_schema',
                     '_model_create': 'create',
                     '_model_delete_by_id': 'delete',
                     '_model_get_by_id': 'get',
                     '_model_get_by_filter': 'filter',
                     '_model_query': 'query',
                     '_model_update_by_id': 'update'}.items():
    globals()[name] = partial(_call_model, method)


def _model_get_first_by_filter(model, filters):
    result = _model_get_by_filter(model, filters)
    if len(result):
        return result[0]
    return None


# set up the default boilerplate functions, then
# allow overrides after that
for d in _get_models():
    model = d.lower()
    sing = model[:-1]

    globals()['%s_get_all' % model] = partial(
        _model_get_all, model)
    globals()['%s_delete_by_id' % sing] = partial(
        _model_delete_by_id, model)
    globals()['%s_get_columns' % sing] = partial(
        _model_get_columns, model)
    globals()['%s_get_first_by_filter' % sing] = partial(
        _model_get_first_by_filter, model)
    globals()['%s_get_by_id' % sing] = partial(
        _model_get_by_id, model)
    globals()['%s_create' % sing] = partial(
        _model_create, model)
    globals()['%s_update_by_id' % sing] = partial(
        _model_update_by_id, model)
    globals()['%s_query' % model] = partial(
        _model_query, model)


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

    stmt1 = sqlalchemy.sql.or_(
        models.Adventures.backend == models.Nodes.backend,
        models.Adventures.backend == 'null')
    stmt2 = sqlalchemy.sql.or_(
        models.Adventures.backend_state == models.Nodes.backend_state,
        models.Adventures.backend_state == 'null')
    adventure_list = models.Adventures.query.join(
        models.Nodes,
        sqlalchemy.sql.and_(stmt1, stmt2, models.Nodes.id == node_id)).all()

    result = [dict((c, getattr(r, c))
                   for c in r.__table__.columns.keys())
              for r in adventure_list]
    return result
