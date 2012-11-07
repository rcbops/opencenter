# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import random
import string
import unittest2


from roush import webapp
from roush.db.database import init_db


class RoushTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(cls.app.config['database_uri'])
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        pass

    def _clean_all(self):
        for what in ['task', 'node', 'fact']:
            all_results = self._model_get_all(what)
            for what_id in [x['id'] for x in all_results]:
                self._model_delete(what, what_id)

    def _valid_rand(self, var_type):
        if var_type == 'INTEGER':
            return random.randrange(1,100)
        elif var_type == 'TEXT':
            return self._random_str(250)
        elif var_type == 'JSON_ENTRY':
            choices = [lambda: self._random_str(10),
                       lambda: self._valid_rand('INTEGER'),
                       lambda: [self._random_str(10) for x in range(10)]]
            return choices()
        elif var_type == 'JSON':
            choices = [lambda: [self._random_str(10) for x in range(10)],
                       lambda: dict([(self._random_str(5),
                                      self._valid_rand('INTEGER'))
                                     for x in range(10)])]
            return choices()
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
        return fn(uri, content_type='application/json', **kwargs)

    def _model_create(self, model, **kwargs):
        resp = self.client.post('/%s/' % self._pluralize(model),
                                content_type='application/json',
                                data=json.dumps(kwargs))

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

    def test_get_schema(self):
        if not hasattr(self, 'base_object'):
            self.skipTest('no base_object')

        self._model_get_schema(self.base_object)

    def test_create(self):
        if not hasattr(self, 'base_object'):
            self.skipTest('no base_object')

        bo = self.base_object
        bop = self._pluralize(bo)

        schema = self._model_get_schema(self.base_object)

        req_fields = [x for x in schema if (schema[x]['required'] == True) and
                      (schema[x]['primary_key'] == False)]
        ro_fields = [x for x in schema if schema[x]['updatable'] == False]

        ids = []

        # make sure we can't create without a non-updatable field
        for field in req_fields:
            full_field_list = req_fields
            full_field_list.remove(field)

            data = dict(zip(full_field_list,
                            [self._valid_rand(schema[x]['type'])
                             for x in full_field_list]))

            self.app.logger.debug('Creating new %s with %s' % (bo, data))

            res = self._client_request('post', '/%s/' % bop, data=data)
            self.app.logger.debug('result: %s: %s' %
                                  (res.status_code, res.data))
            self.assertEquals(res.status_code, 400)
