# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import string
import sys
import time
import unittest2

from functools import partial

from db.database import init_db
import webapp


def _pluralize(what):
    return what + 's'


def _singularize(what):
    return what[:-1]


def model_create(self, model, **kwargs):
    resp = self.client.post('/%s/' % _pluralize(model),
                            content_type='application/json',
                            data=json.dumps(kwargs))

    self.assertEquals(resp.status_code, 201)
    return json.loads(resp.data)[model]


def model_update(self, model, id, **kwargs):
    resp = self.client.put('/%s/%s' % (_pluralize(model), id),
                           content_type='application/json',
                           data=json.dumps(kwargs))
    self.assertEquals(resp.status_code, 200)
    return json.loads(resp.data)[model]


def model_delete(self, model, id):
    resp = self.client.delete('/%s/%s' % (_pluralize(model), id))
    self.assertEquals(resp.status_code, 200)
    out = json.loads(resp.data)
    self.assertEquals(out['status'], 200)
    self.assertEquals(out['message'], '%s deleted' %
                      model.capitalize())


def model_get_by_id(self, model, id):
    resp = self.client.get('/%s/%s' % (_pluralize(model), id))
    self.assertEquals(resp.status_code, 200)
    out = json.loads(resp.data)
    # self.assertEquals(out['status'], 200)
    return out[model]


def model_get_by_filter(self, model, filter_str):
    resp = self.client.post('/%s/filter' % _pluralize(model),
                            content_type='application/json',
                            data=json.dumps({'filter': filter_str}))
    self.app.logger.debug('response: %s' % resp)
    self.assertEquals(resp.status_code, 200)
    out = json.loads(resp.data)
    return out[_pluralize(model)]


def inject_self(self):
    self._model_create = partial(model_create, self)
    self._model_delete = partial(model_delete, self)
    self._model_get_by_id = partial(model_get_by_id, self)
    self._model_filter = partial(model_get_by_filter, self)
    self._model_update = partial(model_update, self)
