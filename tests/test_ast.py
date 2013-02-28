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
from util import OpenCenterTestCase

import opencenter.backends


class AstTests(OpenCenterTestCase):
    def setUp(self):
        if opencenter.backends.primitive_by_name('test.set_test_fact') is None:
            opencenter.backends.load_specific_backend('tests.test',
                                                      'TestBackend')

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
                           key='map_fact',
                           value={'1': '2', '3': '4', '9': '5'})
        self._model_create('facts', node_id=self.node1['id'],
                           key='str_fact', value='azbycxdw')
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
        result = self._model_filter('nodes', 'nth(2, facts.array_fact)')
        self.app.logger.debug('result: %s' % result)
        self.assertEqual(len(result), 0)
        result = self._model_filter('nodes', 'nth("0", facts.array_fact)')
        self.app.logger.debug('result: %s' % result)
        self.assertEqual(len(result), 0)
        self.assertRaises(RuntimeError, self._model_filter,
                          'nodes', 'nth(-1, facts.array_fact)')

    def test_max(self):
        result = self._model_filter('nodes', 'max(facts.array_fact) = 2')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        result = self._model_filter('nodes', 'max(facts.map_fact) = "9"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)
        result = self._model_filter('nodes', 'max(facts.str_fact) = "z"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_str(self):
        self._model_create('facts', node_id=self.node1['id'],
                           key='int',
                           value=3)
        result = self._model_filter('nodes', 'str(facts.int) = "3"')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        self._model_create('facts', node_id=self.node1['id'],
                           key='empty',
                           value='')
        result = self._model_filter('nodes', 'str(facts.empty) = ""')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_int(self):
        self._model_create('facts', node_id=self.node1['id'],
                           key='string',
                           value='3')
        result = self._model_filter('nodes', 'int(facts.string) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        self._model_create('facts', node_id=self.node1['id'],
                           key='zero_int',
                           value=0)
        result = self._model_filter('nodes', 'int(facts.zero_int) = 0')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)
        self._model_create('facts', node_id=self.node1['id'],
                           key='one_int',
                           value=1)
        result = self._model_filter('nodes', 'int(facts.one_int) = 1')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        self._model_create('facts', node_id=self.node1['id'],
                           key='neg_int',
                           value=-1)
        result = self._model_filter('nodes', 'int(facts.neg_int) < 0')
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        # self.assertEquals(len(result), 1)

    def test_count(self):
        result = self._model_filter('nodes', 'count(facts.array_fact) = 2')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        result = self._model_filter('nodes', 'count(facts.map_fact) = 3')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)
        result = self._model_filter('nodes', 'count(facts.str_fact) = 8')
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)
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
        query = 'count(union(facts.array_fact, 2)) > 2'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 0)

    def test_remove(self):
        query = 'count(remove(facts.array_fact, 2)) = 1'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        self._model_create('facts', node_id=self.node1['id'],
                           key='dups_array',
                           value=[1, 1, 2, 3])
        query = 'count(remove(facts.dups_array, 1)) = 3'
        result = self._model_filter('nodes', query)
        self.app.logger.debug('result: %s' % result)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
        query = 'remove(facts.map_fact, "1")'
        self.assertRaisesRegexp(SyntaxError, 'remove on non-list type',
                                self._model_filter, 'nodes', query)

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

    def test_childof(self):
        query = 'childof("container")'
        result = self._model_filter('nodes', query)
        self.assertEqual(len(result), 2)
        query = 'childof("badname")'
        result = self._model_filter('nodes', query)
        self.assertEqual(len(result), 0)
        self.node3 = self._model_create('nodes', name='node3')
        self.node4 = self._model_create('nodes', name='node4')
        self._model_create('facts', node_id=self.node3['id'],
                           key='parent_id', value=self.node4['id'])
        self._model_create('facts', node_id=self.node4['id'],
                           key='parent_id', value=self.node3['id'])
        query = 'childof("node2")'
        result = self._model_filter('nodes', query)
        #this tests for (gets stuck)  infinite loop
        self.assertEqual(len(result), 0)

    def test_printf(self):
        query = 'facts.str_fact = printf("azby%s", "cxdw")'
        result = self._model_filter('nodes', query)
        self.assertEquals(len(result), 1)
        self.assertTrue(result[0]['name'] == 'node1')
    # fix this by db abstraction...
    # def test_017_relations(self):
    #     # this should actually work....
    #     result = self._model_filter('node', 'parent.name="%s"' %
    #                                 self.cluster['name'])
    #     self.app.logger.debug('result: %s' % result)
    #     self.assertEquals(len(result), len(self.nodes))
