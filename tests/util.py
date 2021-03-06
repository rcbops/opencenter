# vim: tabstop=4 shiftwidth=4 softtabstop=4
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
import json
import random
import string
import unittest2
import logging

from opencenter import webapp
from opencenter.db.database import init_db, _memorydb_migrate_db


class OpenCenterTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        ast_logger = logging.getLogger('opencenter.webapp.ast')
        ast_logger.setLevel(logging.INFO)

        cls.app = webapp.WebServer('opencenter',
                                   configfile='tests/test.conf',
                                   debug=True)
        init_db(cls.app.config['database_uri'], migrate=False)
        cls.client = cls.app.test_client()
        cls.logger = cls.app.logger

    @classmethod
    def tearDownClass(cls):
        pass

    def __init__(self, *args, **kwargs):
        super(OpenCenterTestCase, self).__init__(*args, **kwargs)

    def _clean_all(self):
        for what in ['tasks', 'nodes', 'facts', 'filters',
                     'attrs', 'adventures']:
            self._clean_table(what)

    def _clean_table(self, what):
        all_results = self._model_get_all(what)
        for what_id in [x['id'] for x in all_results]:
            self._model_delete(what, what_id)

    def _valid_rand(self, var_type):
        if var_type == 'INTEGER':
            return random.randrange(1, 100)
        elif var_type == 'TEXT':
            return self._random_str(250)
        elif var_type == 'JSON_ENTRY':
            choices = [lambda: self._random_str(10),
                       lambda: self._valid_rand('INTEGER'),
                       lambda: [self._random_str(10) for x in range(10)]]
            return choices[random.randrange(0, len(choices))]()
        elif var_type == 'JSON':
            choices = [lambda: [self._random_str(10) for x in range(10)],
                       lambda: dict([(self._random_str(5),
                                      self._valid_rand('INTEGER'))
                                     for x in range(10)])]
            return choices[random.randrange(0, len(choices))]()
        elif var_type.startswith('VARCHAR'):
            str_len = int(var_type.split('(')[1][:-1])
            return self._random_str(str_len)

        raise ValueError('bad rand type: %s' % var_type)

    def _random_str(self, size=20):
        return "".join(random.choice(string.ascii_lowercase)
                       for x in range(size))

    def _delete_items(self, to_delete=None):
        if to_delete is None:
            to_delete = {}

        for model in to_delete:
            for model_id in to_delete[model]:
                self._model_delete(model, model_id)

    def _pluralize(self, what):
        return what + 's'

    def _singularize(self, what):
        return what[:-1]

    def _get_txid(self, expect_code=200, raw=False):
        resp = self.client.get('/updates')

        self.logger.debug('Got txid: %s' % resp.data)

        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)

        out = json.loads(resp.data)

        if raw:
            return out

        return out['transaction']

    def _stub_node(self, name, facts=None, attrs=None):
        # we do this so much, we might as well just
        # make it a helper
        node = self._model_create('nodes', name=name)
        if facts is None:
            facts = {}

        if attrs is None:
            attrs = {}

        for k, v in facts.items():
            self._model_create('facts', node_id=node['id'],
                               key=k, value=v)

        for k, v in attrs.items():
            self._model_create('attrs', node_id=node['id'],
                               key=k, value=v)

        return node

    def _client_request(self, method, uri, **kwargs):
        fn = getattr(self.client, method)
        self.assertIsNotNone(fn)
        return fn(uri, content_type='application/json',
                  data=json.dumps(kwargs))

    def _model_get_updates(self, model, session, txid,
                           expect_code=200, raw=False):
        resp = self.client.get('/%s/updates/%s/%s' %
                               (model, session, txid))

        self.logger.debug('Got updates: %s' % resp.data)

        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)

        out = json.loads(resp.data)

        if raw:
            return out

        return out['transaction'], out['nodes']

    def _model_create(self, model, please=False,
                      expect_code=201, raw=False, **kwargs):
        url_base = ''
        if not please:
            url_base = '/admin'

        self.logger.debug('Creating %s with %s: ' %
                          (model, kwargs))

        resp = self.client.post('%s/%s/' % (url_base, model),
                                content_type='application/json',
                                data=json.dumps(kwargs))

        self.logger.debug('Create: got %s' % resp.data)
        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)

        if raw:
            return json.loads(resp.data)

        return json.loads(resp.data)[self._singularize(model)]

    def _model_update(self, model, id, please=False,
                      expect_code=200, raw=False, **kwargs):
        url_base = ''
        if not please:
            url_base = '/admin'

        resp = self.client.put('%s/%s/%s' % (url_base, model, id),
                               content_type='application/json',
                               data=json.dumps(kwargs))
        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)

        out = json.loads(resp.data)

        if raw:
            return out

        return out[self._singularize(model)]

    def _model_delete(self, model, id, please=False,
                      expect_code=200, raw=False):
        url_base = ''
        if not please:
            url_base = '/admin'

        resp = self.client.delete('%s/%s/%s' %
                                  (url_base, model, id))
        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)

        out = json.loads(resp.data)

        if raw:
            return out

        self.app.logger.debug('model_delete response: %s' % out)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], '%s deleted' %
                          self._singularize(model).capitalize())

        return out

    def _model_get_by_id(self, model, id, please=False,
                         expect_code=200, raw=False):
        url_base = ''
        if not please:
            url_base = '/admin'

        resp = self.client.get('%s/%s/%s' % (url_base, model, id))
        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)
        out = json.loads(resp.data)
        self.app.logger.debug('model_get_by_id response: %s' % out)
        if raw:
            return out

        return out[self._singularize(model)]

    def _model_filter(self, model, filter_str, please=False,
                      expect_code=200, raw=False):
        url_base = ''
        if not please:
            url_base = '/admin'

        resp = self.client.post('%s/%s/filter' % (url_base, model),
                                content_type='application/json',
                                data=json.dumps({'filter': filter_str}))
        self.app.logger.debug('response: %s' % resp)
        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)
        out = json.loads(resp.data)
        self.app.logger.debug('model_get_by_filter response: %s' % out)

        if raw:
            return out

        return out[model]

    def _model_get_all(self, model, please=False, expect_code=200,
                       raw=False):
        url_base = ''
        if not please:
            url_base = '/admin'

        resp = self.client.get('%s/%s/' % (url_base, model))
        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)
        out = json.loads(resp.data)

        self.app.logger.debug('get_all response: %s' % out)

        if raw:
            return out
        return out[model]

    def _model_get_schema(self, model, please=False, expect_code=200,
                          raw=False):
        url_base = ''
        if not please:
            url_base = '/admin'

        resp = self.client.get('%s/%s/schema' %
                               (url_base, self._pluralize(model)))
        self.app.logger.debug('get_schema response: %s' % resp.data)
        if expect_code is not None:
            self.assertEquals(resp.status_code, expect_code)
        out = json.loads(resp.data)

        if raw:
            return out
        return out['schema']


class ScaffoldedTestCase(OpenCenterTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        ast_logger = logging.getLogger('opencenter.webapp.ast')
        ast_logger.setLevel(logging.INFO)

        cls.app = webapp.WebServer('opencenter',
                                   configfile='tests/test.conf',
                                   debug=True)
        init_db(cls.app.config['database_uri'], migrate=False)
        _memorydb_migrate_db()

        cls.client = cls.app.test_client()
        cls.logger = cls.app.logger

    @classmethod
    def tearDownClass(cls):
        pass

    def __init__(self, *args, **kwargs):
        super(ScaffoldedTestCase, self).__init__(*args, **kwargs)


def _test_fail(self):
    self.assertTrue(False)


def _test_get_schema(self):
    self._model_get_schema(self.base_object)


def _test_missing_create_field(self, missing_field, expected_code):
    bo = self.base_object
    bop = self._pluralize(bo)

    schema = self._model_get_schema(bo)
    all_fields = [x for x in schema]
    all_fields.remove('id')

    data = dict(zip(all_fields,
                    [self._valid_rand(schema[x]['type'])
                     for x in all_fields]))

    data.pop(missing_field)

    # special case tasks -- need schema for enum type
    if bo == 'task' and 'state' in data:
        data['state'] = 'running'

    self.logger.debug('creating with data %s (missing %s)' %
                      (data, missing_field))

    _test_request_returns(self, 'post', '/admin/%s/' % bop, data,
                          expected_code)


def _add_test_data(self, model):
    schema = self._model_get_schema(model)
    all_fields = [x for x in schema]
    all_fields.remove('id')

    data = dict(zip(all_fields,
                    [self._valid_rand(schema[x]['type'])
                     for x in all_fields]))
    self._client_request('post', '/admin/%s/' % self._pluralize(model), **data)


def _test_seed_data_request_returns(self, method, url, data,
                                    expected_code, seed_data):
    for model, num in seed_data.iteritems():
        for each in range(num):
            _add_test_data(self, model)
    _test_request_returns(self, method, url, data, expected_code)


def _test_request_returns(self, method, url, data, expected_code):
    self.logger.debug('sending %s to %s, with data: %s' % (method, url, data))
    resp = self._client_request(method, url, **data)
    self.logger.debug('got status_code %d, %s' % (resp.status_code,
                                                  resp.data))

    self.assertEquals(resp.status_code, expected_code)


def inject(cls):
    model = getattr(cls, 'base_object', None)

    if model is None:
        raise SyntaxError("missing base object")

    test = lambda self: _test_get_schema(self)
    test.__name__ = 'test_get_primitive_schema'
    setattr(cls, test.__name__, test)

    app = webapp.WebServer('opencenter',
                           configfile='tests/test.conf',
                           debug=True)

    init_db(app.config['database_uri'], migrate=False)
    client = app.test_client()
    logger = app.logger

    resp = client.get('/admin/%ss/schema' % model)
    out = json.loads(resp.data)
    schema = out['schema']

    all_fields = [x for x in schema]
    all_fields.remove('id')
    req_fields = [x for x in schema if (schema[x]['required'] is True) and
                  (schema[x]['primary_key'] is False)]

    for field in req_fields:
        test = lambda self, field=field: _test_missing_create_field(
            self, field, 400)
        test.__name__ = str('test_create_%s_without_%s_returns_%d' %
                            (model, field, 400))

        setattr(cls, test.__name__, test)

    for field in all_fields:
        if field not in req_fields:
            test = lambda self, field=field: _test_missing_create_field(
                self, field, 201)
            test.__name__ = str('test_create_%s_without_%s_returns_%d' %
                                (model, field, 201))

            setattr(cls, test.__name__, test)

    test = lambda self:  _test_request_returns(
        self, 'get', '/admin/%s/999999' % self._pluralize(self.base_object),
        {}, 404)
    test.__name__ = str('test_request_bad_id_returns_404')
    setattr(cls, test.__name__, test)

    return cls
