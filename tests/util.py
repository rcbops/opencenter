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
        for what in ['task', 'node', 'fact', 'filter']:
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

    def _model_create(self, model, **kwargs):
        resp = self.client.post('/%s/' % self._pluralize(model),
                                content_type='application/json',
                                data=json.dumps(kwargs))

        self.logger.debug('Create: got %s' % json.loads(resp.data)[model])
        self.assertEquals(resp.status_code, 201)
        return json.loads(resp.data)[model]

    def _model_update(self, model, id, **kwargs):
        resp = self.client.put('/%s/%s' % (self._pluralize(model), id),
                               content_type='application/json',
                               data=json.dumps(kwargs))
        self.assertEquals(resp.status_code, 200)
        return json.loads(resp.data)[model]

    def _model_delete(self, model, id):
        resp = self.client.delete('/%s/%s' % (self._pluralize(model), id))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.app.logger.debug('model_delete response: %s' % out)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], '%s deleted' %
                          model.capitalize())

    def _model_get_by_id(self, model, id):
        resp = self.client.get('/%s/%s' % (self._pluralize(model), id))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.app.logger.debug('model_get_by_id response: %s' % out)
        return out[model]

    def _model_filter(self, model, filter_str):
        resp = self.client.post('/%s/filter' % self._pluralize(model),
                                content_type='application/json',
                                data=json.dumps({'filter': filter_str}))
        self.app.logger.debug('response: %s' % resp)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.app.logger.debug('model_get_by_filter response: %s' % out)
        return out[self._pluralize(model)]

    def _model_get_all(self, model):
        resp = self.client.get('/%s/' % self._pluralize(model))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.app.logger.debug('get_all response: %s' % out)
        return out[self._pluralize(model)]

    def _model_get_schema(self, model):
        resp = self.client.get('/%s/schema' % self._pluralize(model))
        self.app.logger.debug('get_schema response: %s' % resp.data)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
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
    resp = self._client_request('post', '/%s/' % bop, **data)

    self.logger.debug('got status_code of %d, %s' % (resp.status_code,
                                                     resp.data))
    self.assertEquals(resp.status_code, expected_code)
    if expected_code == 400:
        self.assertTrue('missing required' in json.loads(resp.data)['message'])


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

    resp = client.get('%ss/schema' % model)
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

    return cls
