# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import random
import string
import unittest2


from roush import webapp
from roush.db.database import init_db


class RoushTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.app = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(cls.app.config['database_uri'])
        cls.client = cls.app.test_client()
        cls.logger = cls.app.logger

    @classmethod
    def tearDownClass(cls):
        pass

    def __init__(self, *args, **kwargs):
        super(RoushTestCase, self).__init__(*args, **kwargs)

    def _clean_all(self):
        for what in ['tasks', 'nodes', 'facts', 'filters', 'attrs']:
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

    def _pluralize(self, what):
        return what + 's'

    def _singularize(self, what):
        return what[:-1]

    def _client_request(self, method, uri, **kwargs):
        fn = getattr(self.client, method)
        self.assertIsNotNone(fn)
        return fn(uri, content_type='application/json',
                  data=json.dumps(kwargs))

    def _model_create(self, model, please=False,
                      expect_code=201, raw=False, **kwargs):
        url_base = ''
        if not please:
            url_base = '/admin'

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

    self.logger.debug('creating with data %s (missing %s)' %
                      (data, missing_field))

    _test_request_returns(self, 'post', '/admin/%s/' % bop, data,
                          expected_code)


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

    app = webapp.Thing('roush', configfile='test.conf', debug=True)
    init_db(app.config['database_uri'])
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
