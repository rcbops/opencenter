# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest2
import util

from db.database import init_db
import webapp


class FiltersTests(unittest2.TestCase):
    def __init__(self, *args, **kwargs):
        super(FiltersTests, self).__init__(*args, **kwargs)
        util.inject_self(self)

    def setUp(self):
        self.app = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(self.app.config['database_uri'])
        self.client = self.app.test_client()

        self.nodes = {}

        for d in range(1, 9):
            self.nodes['node-%s' % d] = self._model_create('node',
                                                           name='node-%s' % d)

        self.cluster = self._model_create('node', name='cluster')

        for name, node in self.nodes.items():
            self._model_update('node', node['id'],
                               parent_id=self.cluster['id'])

    def tearDown(self):
        for name, node in self.nodes.items():
            self._model_delete('node', node['id'])

        self._model_delete('node', self.cluster['id'])

    def test_001_int_equality(self):
        result = self._model_filter('node', 'parent_id=%d' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))

    def test_002_str_equality(self):
        result = self._model_filter('node', 'name=\'node-1\'')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)

    def test_003_str_format(self):
        result = self._model_filter('node', 'name="node-1"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)

    def test_004_greater_than(self):
        result = self._model_filter('node', 'parent_id > 0')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))

    def test_005_less_than(self):
        result = self._model_filter('node', 'parent_id < 999')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))

    def test_006_identity_filter(self):
        result = self._model_filter('node', 'true')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_007_unary_negative(self):
        result = self._model_filter('node', 'parent_id !< 999')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_008_less_than_equal(self):
        result = self._model_filter('node', 'parent_id <= %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))
        result = self._model_filter('node', 'parent_id < %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_009_greater_than_equal(self):
        result = self._model_filter('node', 'parent_id >= %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))
        result = self._model_filter('node', 'parent_id > %s' %
                                    self.cluster['id'])
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_010_in(self):
        self._model_create('fact', node_id=self.cluster['id'],
                           key='array',
                           value=[1, 2, 3])
        result = self._model_filter('node', '3 in facts.array')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_011_nth(self):
        result = self._model_filter('node', 'nth(0, facts.array) = 1')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_012_max(self):
        result = self._model_filter('node', 'max(facts.array) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_013_str(self):
        self._model_create('fact', node_id=self.cluster['id'],
                           key='int',
                           value=3)
        result = self._model_filter('node', 'str(facts.int) = "3"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_014_int(self):
        self._model_create('fact', node_id=self.cluster['id'],
                           key='string',
                           value='3')
        result = self._model_filter('node', 'int(facts.string) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_015_count(self):
        result = self._model_filter('node', 'count(facts.array) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes) + 1)

    def test_016_filter(self):
        query = 'count(filter("nodes", printf("parent_id=%s", parent_id))) > 1'
        result = self._model_filter('node', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), len(self.nodes))


    # fix this by db abstraction...
    # def test_017_relations(self):
    #     # this should actually work....
    #     result = self._model_filter('node', 'parent.name="%s"' %
    #                                 self.cluster['name'])
    #     self.app.logger.debug('result: %s' % result)
    #     self.assertEquals(len(result), len(self.nodes))
