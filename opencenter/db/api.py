#! /usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

import logging
from functools import partial

from opencenter.db import abstraction
import opencenter.webapp.ast

_cached_apis = {}
use_cached_api = True
stupid_amount_of_logging = False


class OpenCenterApi(object):
    def __init__(self):
        self.model_list = {}
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))

    def __repr__(self):
        types = ["%s:%s" % (x, self.model_list[x].__class__.__name__)
                 for x in self.model_list]
        types = ",".join(types)

        return '<OpenCenterApi: %s>' % types

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

    def invert_expression(self, expression):
        # rather than raising an exception on an un-invertable
        # expression, we'll log it and return none.
        result = None

        try:
            result = opencenter.webapp.ast.invert_expression(expression)
        except SyntaxError as e:
            self.logger.error('Error inverting expression: %s: %s' %
                              (expression, str(e)))

        return result

    def regularize_expression(self, expression):
        try:
            return opencenter.webapp.ast.regularize_expression(expression)
        except SyntaxError as e:
            self.logger.error('Error regularizing expression %s: %s' %
                              (expression, str(e)))
            raise

    def apply_expression(self, node_id, expression):
        # again, we should probably have a standard namespace for
        # applying expressions
        try:
            return opencenter.webapp.ast.apply_expression(
                node_id, expression, self)
        except SyntaxError as e:
            self.logger.error('Error applying %s: %s' %
                              (expression, str(e)))
            raise

    def concrete_expression(self, expression, ns={}):
        # I think there should be a standard default namespace, including
        # nodes[<id>], self, and other things... this is here so we
        # can determine a regular namespace for evaluating expressions.  Right
        # now, there is no real reason for it to be here.
        try:
            return opencenter.webapp.ast.concrete_expression(expression, ns)
        except SyntaxError as e:
            self.logger.error('Error concreteing %s: %s' %
                              (expression, str(e)))
            raise

    def _get_models(self):
        return self.model_list.keys()

    def _call_model(self, function, model, *args, **kwargs):
        model = model.lower()

        if not model in self.model_list:
            raise KeyError('unknown model %s' % model)

        if not hasattr(self.model_list[model], function):
            raise ValueError('unknown model function %s' % function)

        if stupid_amount_of_logging:
            self.logger.debug('calling %s on model %s with %s, %s' %
                              (function, model, args, kwargs))

        result = getattr(self.model_list[model], function)(*args, **kwargs)

        if stupid_amount_of_logging:
            self.logger.debug('return from %s on model %s: %s' %
                              (function, model, result))

        return result

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

    def _model_query(self, model, query):
        return self._call_model('query', model, query)

    def _model_get_first_by_query(self, model, query):
        return self._call_model('first_by_query', model, query)

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
        setattr(self, '%s_get_by_id' % sing,
                partial(self._model_get_by_id, model))
        setattr(self, '%s_create' % sing,
                partial(self._model_create, model))
        setattr(self, '%s_update_by_id' % sing,
                partial(self._model_update_by_id, model))
        setattr(self, '%s_query' % model,
                partial(self._model_query, model))
        setattr(self, '%s_get_first_by_query' % sing,
                partial(self._model_get_first_by_query, model))


def api_from_endpoint(endpoint):
    if 'endpoint-based-%s' % endpoint in _cached_apis:
        return _cached_apis['endpoint-based-%s' % endpoint]

    from opencenterclient import client
    from opencenter.db import models

    new_api = OpenCenterApi()
    ep = client.OpenCenterEndpoint(endpoint)

    # the index page should be wired up right, and we should
    # have an api call to get all the object types
    for model_name in ['nodes', 'filters', 'tasks',
                       'adventures', 'facts', 'attrs']:
        model = getattr(models, model_name.title())
        api_abstraction = abstraction.APIAbstraction(new_api, model,
                                                     model_name, ep)
        new_api.add_model(model_name, api_abstraction)

    _cached_apis['endpoint-based-%s' % endpoint] = new_api
    return new_api


def api_from_models():
    if 'model-based' in _cached_apis:
        return _cached_apis['model-based']

    from opencenter import backends
    from opencenter.db import models
    from opencenter.db import inmemory

    backends.load()

    new_api = OpenCenterApi()

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
    new_api = OpenCenterApi()

    for name, backend in backed_api.model_list.items():
        abst = abstraction.EphemeralAbstraction(new_api, backend.model,
                                                name, backend)
        new_api.add_model(name, abst)

    # if use_cached_api:
    #     cached_api = cached_api_from_api(new_api)
    #     return cached_api
    # else:
    return new_api


def cached_api_from_api(backed_api):
    # run through the existing backends and create a new
    # ephemeral data source backed by those backends
    new_api = OpenCenterApi()

    for name, backend in backed_api.model_list.items():
        abst = abstraction.CachedAbstraction(new_api, backend.model,
                                             name, backend)
        new_api.add_model(name, abst)

    return new_api
