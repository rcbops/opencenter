# vim: tabstop=4 shiftwidth=4 softtabstop=4
from util import RoushTestCase

import roush.backends


class AstTests(RoushTestCase):
    def setUp(self):
        if roush.backends.primitive_by_name('test.set_test_fact') is None:
            roush.backends.load_specific_backend('tests.test', 'TestBackend')

        self.container = self._model_create('nodes', name='container')
        self.node1 = self._model_create('nodes', name='node1')
        self.node2 = self._model_create('nodes', name='node2')

        self._model_create('facts', node_id=self.node1['id'],
                           key='parent_id',
                           value=self.container['id'])

        self._model_create('facts', node_id=self.node2['id'],
                           key='parent_id',
                           value=self.container['id'])

        self._model_create('facts', node_id=self.node1['id'],
                           key='array_fact', value=[1, 2])
        self._model_create('facts', node_id=self.node1['id'],
                           key='node1', value=True)
        self._model_create('facts', node_id=self.node1['id'],
                           key='selfref', value='node1')

    def tearDown(self):
        self._clean_all()

    def test_int_equality(self):
        result = self._model_filter('nodes', 'facts.parent_id=%d' %
                                    self.container['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 2)

    def test_str_equality(self):
        result = self._model_filter('nodes', 'name=\'node1\'')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_str_format(self):
        result = self._model_filter('nodes', 'name="node1"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_other_str_format(self):
        result = self._model_filter('nodes', "name='node1'")
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_greater_than(self):
        result = self._model_filter('nodes', 'facts.parent_id > 0')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 2)

    def test_less_than(self):
        result = self._model_filter('nodes', 'facts.parent_id < 999')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 2)

    def test_identity_filter(self):
        result = self._model_filter('nodes', 'true')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 3)

    def test_unary_not(self):
        result = self._model_filter('nodes', 'facts.parent_id !< 999')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_less_than_equal(self):
        result = self._model_filter('nodes', 'facts.parent_id <= %s' %
                                    self.container['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 2)

        result = self._model_filter('nodes', 'facts.parent_id < %s' %
                                    self.container['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_greater_than_equal(self):
        result = self._model_filter('nodes', 'facts.parent_id >= %s' %
                                    self.container['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 2)
        result = self._model_filter('nodes', 'facts.parent_id > %s' %
                                    self.container['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_in(self):
        # we aren't testing inheritance here, that's in the inheritance
        # tests.
        result = self._model_filter('nodes', '2 in facts.array_fact')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_nth(self):
        result = self._model_filter('nodes', 'nth(0, facts.array_fact) = 1')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_max(self):
        result = self._model_filter('nodes', 'max(facts.array_fact) = 2')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_str(self):
        self._model_create('facts', node_id=self.node1['id'],
                           key='int',
                           value=3)
        result = self._model_filter('nodes', 'str(facts.int) = "3"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_int(self):
        self._model_create('facts', node_id=self.node1['id'],
                           key='string',
                           value='3')
        result = self._model_filter('nodes', 'int(facts.string) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        # self.assertEquals(len(result), 1)

    def test_count(self):
        result = self._model_filter('nodes', 'count(facts.array_fact) = 2')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        # self.assertEquals(len(result), 1)

    def test_filter(self):
        query = 'count(filter("nodes", "facts.parent_id=' \
                '{facts.parent_id}")) > 1'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 2)

    def test_union(self):
        query = 'count(union(facts.array_fact, 3)) > 1'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_union_of_null(self):
        query = '("node" in name) and (count(union(facts.array_fact, 3)) = 1)'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        # node 2
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node2')

    def test_identifier_interpolation(self):
        query = 'facts.{name} = true'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    def test_string_interpolation(self):
        query = 'facts.selfref = "{name}"'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')

    # fix this by db abstraction...
    # def test_017_relations(self):
    #     # this should actually work....
    #     result = self._model_filter('node', 'parent.name="%s"' %
    #                                 self.cluster['name'])
    #     self.app.logger.debug('result: %s' % result)
    #     self.assertEquals(len(result), len(self.nodes))
