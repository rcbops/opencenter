# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest2

from util import RoushTestCase
from util import inject


class FactsTests(RoushTestCase):
    base_object = 'fact'

    def setUp(self):
        self._clean_all()

        self.c2 = self._model_create('node',
                                     name=self._random_str())
        self.c1 = self._model_create('node',
                                     name=self._random_str(),
                                     parent_id=self.c2['id'])
        self.n1 = self._model_create('node',
                                     name=self._random_str(),
                                     parent_id=self.c1['id'])

    def tearDown(self):
        c2_facts = self._model_filter('fact',
                                      'node_id=%s' % self.c2['id'])

        c1_facts = self._model_filter('fact',
                                      'node_id=%s' % self.c1['id'])

        n1_facts = self._model_filter('fact',
                                      'node_id=%s' % self.n1['id'])

        for fact_id in [x['id'] for x in c2_facts + c1_facts + n1_facts]:
            self.app.logger.debug('deleting fact %s' % fact_id)
            self._model_delete('fact', fact_id)

        self._model_delete('node', self.n1['id'])
        self._model_delete('node', self.c2['id'])
        self._model_delete('node', self.c1['id'])

        all_facts = self._model_get_all('fact')
        all_nodes = self._model_get_all('node')

    def test_001_add_fact(self):
        self._model_create('fact', node_id=self.n1['id'],
                           key='node_data',
                           value='blah')

        n1_facts = self._model_get_by_id('node', self.n1['id'])['facts']

        self.assertEquals(n1_facts['node_data'], 'blah')

    def test_002_fact_inheritance_clobber(self):
        f1 = self._model_create('fact', node_id=self.n1['id'],
                            key="clobbered",
                            value="should be overridden")
        f2 = self._model_create('fact', node_id=self.c1['id'],
                                key='clobbered',
                                value='blah')
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts']['clobbered'], 'blah')
        self._model_delete('fact', f2['id'])
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts']['clobbered'], 'should be overridden')
        self._model_delete('fact', f1['id'])

#    def test_003_fact_inheritance_default

    # def test_003_conflicting_facts(self):
    #     # currently, this is allowed, and parents override children.
    #     # The API itself should _probably_ disallow fact conflicts
    #     self._model_create('fact', node_id=self.n1['id'],
    #                        key='node_data',
    #                        value='blah')

    #     c1_fact = self._model_create('fact', node_id=self.c1['id'],
    #                                  key='node_data',
    #                                  value='c1override')

    #     n1 = self._model_get_by_id('node', self.n1['id'])
    #     self.assertEquals(n1['facts']['node_data'], 'c1override')

    #     c2_fact = self._model_create('fact', node_id=self.c2['id'],
    #                                  key='node_data',
    #                                  value='c2override')

    #     n1 = self._model_get_by_id('node', self.n1['id'])
    #     self.assertEquals(n1['facts']['node_data'], 'c2override')

    #     self._model_delete('fact', c2_fact['id'])
    #     n1 = self._model_get_by_id('node', self.n1['id'])
    #     self.assertEquals(n1['facts']['node_data'], 'c1override')

    #     self._model_delete('fact', c1_fact['id'])
    #     n1 = self._model_get_by_id('node', self.n1['id'])
    #     self.assertEquals(n1['facts']['node_data'], 'blah')

    def test_updating_facts(self):
        self._model_create('fact', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value')
        # now, do a create...
        self._model_create('fact', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value2')
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts']['test_fact'], 'test_value2')

    def test_list_all_facts(self):
        self._model_create('fact', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value')
        result = self._model_get_all('fact')
        self.assertEquals(len(result), 1)

    def test_request_bad_fact(self):
        resp = self.client.get('/facts/9999')
        self.assertEquals(resp.status_code, 404)

    def update_bad_fact(self):
        resp = self.client.put('/facts/9999',
                               content_type='application/json',
                               data=json.dumps({'value': 'test'}))
        self.assertEquals(resp.status_code, 404)

    def test_request_fact(self):
        fact = self._model_create('fact', node_id=self.n1['id'],
                                  key='test_fact',
                                  value='test_value')
        self.app.logger.debug('fact: %s' % fact)
        self._model_get_by_id('fact', fact['id'])


FactsTests = inject(FactsTests)
