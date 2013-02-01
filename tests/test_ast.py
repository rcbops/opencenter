# vim: tabstop=4 shiftwidth=4 softtabstop=4
from util import RoushTestCase

import roush.backends


class AstTests(RoushTestCase):
    def setUp(self):
        if roush.backends.primitive_by_name('test.set_test_fact') is None:
            roush.backends.load_specific_backend('tests.test', 'TestBackend')

        self._clean_all()

        self.nodes = {}

        for d in range(1, 9):
            self.nodes['node-%s' % d] = self._model_create('nodes',
                                                           name='node-%s' % d)

        self.cluster = self._model_create('nodes', name='cluster')

        for name, node in self.nodes.items():
            self._model_create('facts', node_id=node['id'],
                               key='parent_id',
                               value=self.cluster['id'])

        self._model_create('facts', node_id=self.nodes['node-1']['id'],
                           key='array_fact', value=[1, 2])
        self._model_create('facts', node_id=self.nodes['node-1']['id'],
                           key='node-1', value=True)
        self._model_create('facts', node_id=self.nodes['node-1']['id'],
                           key='selfref', value='node-1')

    def tearDown(self):
        for name, node in self.nodes.items():
            self._model_delete('nodes', node['id'])

        self._model_delete('nodes', self.cluster['id'])

    def test_001_int_equality(self):
        result = self._model_filter('nodes', 'facts.parent_id=%d' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))

    def test_002_str_equality(self):
        result = self._model_filter('nodes', 'name=\'node-1\'')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)

    def test_003_str_format(self):
        result = self._model_filter('nodes', 'name="node-1"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)

    def test_004_greater_than(self):
        result = self._model_filter('nodes', 'facts.parent_id > 0')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))

    def test_005_less_than(self):
        result = self._model_filter('nodes', 'facts.parent_id < 999')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))

    def test_006_identity_filter(self):
        result = self._model_filter('nodes', 'true')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_007_unary_negative(self):
        result = self._model_filter('nodes', 'facts.parent_id !< 999')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_008_less_than_equal(self):
        result = self._model_filter('nodes', 'facts.parent_id <= %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))
        result = self._model_filter('nodes', 'facts.parent_id < %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_009_greater_than_equal(self):
        result = self._model_filter('nodes', 'facts.parent_id >= %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))
        result = self._model_filter('nodes', 'facts.parent_id > %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_010_in(self):
        self._model_create('facts', node_id=self.cluster['id'],
                           key='array',
                           value=[1, 2, 3])
        result = self._model_filter('nodes', '3 in facts.array')
        self.app.logger.debug('result: %s' % result)
        # non-inheritable facts
        self.assertEquals(len(result), len(self.nodes) + 1)
        # self.assertEquals(len(result), 1)

    def test_011_nth(self):
        self._model_create('facts', node_id=self.cluster['id'],
                           key='array',
                           value=[1, 2, 3])
        result = self._model_filter('nodes', 'nth(0, facts.array) = 1')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)
        # self.assertEquals(len(result), 1)

    def test_012_max(self):
        self._model_create('facts', node_id=self.cluster['id'],
                           key='array',
                           value=[1, 2, 3])
        result = self._model_filter('nodes', 'max(facts.array) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)
        # self.assertEquals(len(result), 1)

    def test_013_str(self):
        self._model_create('facts', node_id=self.cluster['id'],
                           key='int',
                           value=3)
        result = self._model_filter('nodes', 'str(facts.int) = "3"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)
        # self.assertEquals(len(result), 1)

    def test_014_int(self):
        self._model_create('facts', node_id=self.cluster['id'],
                           key='string',
                           value='3')
        result = self._model_filter('nodes', 'int(facts.string) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)
        # self.assertEquals(len(result), 1)

    def test_015_count(self):
        self._model_create('facts', node_id=self.cluster['id'],
                           key='array',
                           value=[1, 2, 3])
        result = self._model_filter('nodes', 'count(facts.array) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)
        # self.assertEquals(len(result), 1)

    def test_016_filter(self):
        query = 'count(filter("nodes", "facts.parent_id=' \
                '{facts.parent_id}")) > 1'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))

    def test_017_union(self):
        query = 'count(union(facts.array_fact, 3)) > 1'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node-1')

    def test_018_union_of_null(self):
        query = '("node" in name) and (count(union(facts.array_fact, 3)) = 1)'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) - 1)

    def test_019_identifier_interpolation(self):
        query = 'facts.{name} = true'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)

    def test_020_string_interpolation(self):
        query = 'facts.selfref = "{name}"'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)

    # fix this by db abstraction...
    # def test_017_relations(self):
    #     # this should actually work....
    #     result = self._model_filter('node', 'parent.name="%s"' %
    #                                 self.cluster['name'])
    #     self.app.logger.debug('result: %s' % result)
    #     self.assertEquals(len(result), len(self.nodes))
