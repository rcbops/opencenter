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

    def _random_str(self, size=20):
        return "".join(random.choice(string.ascii_lowercase) for x in range(size))

    def _pluralize(self, what):
        return what + 's'

    def _singularize(self, what):
        return what[:-1]

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

        ids=[]

        schema = self._model_get_schema(self.base_object)
