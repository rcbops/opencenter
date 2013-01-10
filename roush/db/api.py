# vim: tabstop=4 shiftwidth=4 softtabstop=4
# tab stops are 8.  ^^ this is wrong

import logging
from functools import partial

import abstraction


_cached_apis = {}
use_cached_api = True


class RoushApi(object):
    def __init__(self):
        self.model_list = {}
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))

    def destroy_cache(self):
        for model, backend in self.model_list.items():
            backend.destroy_cache()

    def transactions(self):
        result = {}
        for model, backend in self.model_list.items():
            if getattr(backend, 'transactions', None) is not None:
                trans = backend.transactions()
                if trans is not None:
                    result[model] = trans

        return result

    def _get_models(self):
        return self.model_list.keys()

    def _call_model(self, function, model, *args, **kwargs):
        model = model.lower()

        if not model in self.model_list:
            raise KeyError('unknown model %s' % model)

        if not hasattr(self.model_list[model], function):
            raise ValueError('unknown model function %s' % function)

        return getattr(self.model_list[model], function)(*args, **kwargs)

    def _model_get_all(self, model):
        return self._call_model('get_all', model)

    def _model_get_by_id(self, model, id):
        return self._call_model('get', model, id)

    def _model_get_columns(self, model):
        return self._call_model('get_columns', model)

    def _model_get_schema(self, model):
        return self._call_model('get_schema', model)

    def _model_create(self, model, data):
        return self._call_model('create', model, data)

    def _model_delete_by_id(self, model, id):
        return self._call_model('delete', model, id)

    def _model_get_by_filter(self, model, filters):
        return self._call_model('filter', model, filters)

    def _model_get_first_by_filter(self, model, filters):
        return self._call_model('first_by_filter', model, filters)

    def _model_query(self, model, query):
        return self._call_model('query', model, query)

    def _model_update_by_id(self, model, id, data):
        return self._call_model('update', model, id, data)

    def add_model(self, name, abstracted_backend):
        model = name.lower()
        sing = model[:-1]

        self.model_list[model] = abstracted_backend

        setattr(self, '%s_get_all' % model,
                partial(self._model_get_all, model))
        setattr(self, '%s_delete_by_id' % sing,
                partial(self._model_delete_by_id, model))
        setattr(self, '%s_get_columns' % sing,
                partial(self._model_get_columns, model))
        setattr(self, '%s_get_first_by_filter' % sing,
                partial(self._model_get_first_by_filter, model))
        setattr(self, '%s_get_by_id' % sing,
                partial(self._model_get_by_id, model))
        setattr(self, '%s_create' % sing,
                partial(self._model_create, model))
        setattr(self, '%s_update_by_id' % sing,
                partial(self._model_update_by_id, model))
        setattr(self, '%s_query' % model,
                partial(self._model_query, model))


def api_from_endpoint(endpoint):
    if 'endpoint-based-%s' % endpoint in _cached_apis:
        return _cached_apis['endpoint-based-%s' % endpoint]

    from roushclient import client
    from roush.db import models

    new_api = RoushApi()
    ep = client.RoushEndpoint(endpoint)

    # the index page should be wired up right, and we should
    # have an api call to get all the object types
    for model_name in ['nodes', 'filters', 'tasks',
                       'adventures', 'facts']:
        model = getattr(models, model_name.title())
        api_abstraction = abstraction.APIAbstraction(new_api, model,
                                                     model_name, ep)
        new_api.add_model(model_name, api_abstraction)

    _cached_apis['endpoint-based-%s' % endpoint] = new_api
    return new_api


def api_from_models():
    if 'model-based' in _cached_apis:
        return _cached_apis['model-based']

    from roush import backends
    from roush.db import models
    from roush.db import inmemory

    backends.load()

    new_api = RoushApi()

    for d in dir(models):
        abst = None
        model_name = d.lower()
        model = getattr(models, d)

        if type(models.Nodes) == type(getattr(models, d)) and d != 'Base':
            abst = abstraction.SqlAlchemyAbstraction(new_api, model,
                                                     model_name)
        elif isinstance(getattr(models, d), type) and \
                issubclass(model, inmemory.InMemoryBase) and \
                d != 'Primitives':
            abst = abstraction.InMemoryAbstraction(new_api, model, d, {})
        elif d == 'Primitives':
            # these run off the backend.backend_primitives dict.
            abst = abstraction.InMemoryAbstraction(new_api, model, d,
                                                   backends.backend_primitives)

        if abst is not None:
            new_api.add_model(d, abst)

    if use_cached_api:
        cached_api = cached_api_from_api(new_api)
        _cached_apis['model-based'] = cached_api
        return cached_api
    else:
        _cached_apis['model-based'] = new_api
        return new_api


def ephemeral_api_from_api(backed_api):
    # run through the existing backends and create a new
    # ephemeral data source backed by those backends
    new_api = RoushApi()

    for name, backend in backed_api.model_list.items():
        abst = abstraction.EphemeralAbstraction(new_api, backend.model,
                                                name, backend)
        new_api.add_model(name, abst)

    if use_cached_api:
        cached_api = cached_api_from_api(new_api)
        return cached_api
    else:
        return new_api


def cached_api_from_api(backed_api):
    # run through the existing backends and create a new
    # ephemeral data source backed by those backends
    new_api = RoushApi()

    for name, backend in backed_api.model_list.items():
        abst = abstraction.CachedAbstraction(new_api, backend.model,
                                             name, backend)
        new_api.add_model(name, abst)

    return new_api
