#
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

import opencenter.db.api as db_api
from opencenter.webapp import ast


api = db_api.api_from_models()


class ExpressionTestCase(OpenCenterTestCase):
    def setUp(self):
        self.nodes = {}
        self.interfaces = {}

        self.nodes['node-1'] = self._model_create('nodes', name='node-1')
        self.interfaces['chef'] = self._model_create('filters', name='chef',
                                                     filter_type='interface',
                                                     expr='facts.x = true')
        self.nodes['container'] = self._model_create('nodes', name='container')

    def tearDown(self):
        self._clean_all()

    def _run_expression(self, node, expression, ns={}):
        builder = ast.FilterBuilder(ast.FilterTokenizer(), expression,
                                    api=api)
        root_node = builder.build()
        return root_node.eval_node(node, symbol_table=ns)

    def _simple_expression(self, expression):
        node = self._model_get_by_id('nodes', self.nodes['node-1']['id'])
        return self._run_expression(node,
                                    'nodes: %s' % expression)

    def _invert_expression(self, expression, ns={}):
        builder = ast.FilterBuilder(ast.FilterTokenizer(), expression)
        root_node = builder.build()
        return root_node.invert()

    def _eval_expression(self, expression, node_id, ns={}):
        ephemeral_api = db_api.ephemeral_api_from_api(api)
        builder = ast.FilterBuilder(ast.FilterTokenizer(), expression,
                                    api=ephemeral_api)
        node = ephemeral_api._model_get_by_id('nodes', node_id)
        builder.eval_node(node, symbol_table=ns)
        new_node = ephemeral_api._model_get_by_id('nodes', node_id)
        return new_node

    def test_bad_interface(self):
        expression = "ifcount('blahblah') > 0"
        self.assertRaises(SyntaxError, self._run_expression,
                          self.nodes['node-1'], expression)

    def test_zero_ifcount(self):
        expression = "ifcount('chef') > 0"
        result = self._run_expression(self.nodes['node-1'], expression)
        self.logger.debug('Got result: %s' % result)
        self.assertEquals(result, False)

    def test_valid_ifcount(self):
        expression = "ifcount('chef') > 0"
        self._model_create('facts', node_id=self.nodes['node-1']['id'],
                           key='x', value=True)
        result = self._run_expression(self.nodes['node-1'], expression)
        self.logger.debug('Got result: %s' % result)
        self.assertEquals(result, True)

    def test_invert_equals(self):
        expression = "facts.test = 'test'"
        result = self._invert_expression(expression)
        self.assertEquals(result, ["facts.test := 'test'"])

    def test_invert_and(self):
        expression = "facts.test='test' and facts.x='x'"
        result = self._invert_expression(expression)
        self.assertTrue("facts.test := 'test'" in result)
        self.assertTrue("facts.x := 'x'" in result)

    def test_invert_in(self):
        expression = "'test' in facts.foo"
        result = self._invert_expression(expression)
        self.assertTrue("facts.foo := union(facts.foo, 'test')" in result)
        self.assertEquals(len(result), 1)

    def test_invert_not_in(self):
        expression = "'test' !in facts.foo"
        result = self._invert_expression(expression)
        self.assertTrue("facts.foo := remove(facts.foo, 'test')" in result)
        self.assertEquals(len(result), 1)

    def test_eval_assign(self):
        node_id = self.nodes['node-1']['id']
        expression = "facts.parent_id := %d" % int(
            self.nodes['container']['id'])

        node = self._eval_expression(expression, node_id)
        self.assertEquals(node['facts'].get('parent_id', None),
                          self.nodes['container']['id'])

    def test_eval_union(self):
        node_id = self.nodes['node-1']['id']
        expression = "facts.woof := union(facts.woof, 3)"

        node = self._eval_expression(expression, node_id)
        self.assertEquals(node['facts']['woof'], [3])

    def test_eval_remove(self):
        node_id = self.nodes['node-1']['id']
        fact = self._model_create('facts', node_id=node_id,
                                  key='array_fact', value=[1, 2])

        expression = 'facts.array_fact := remove(facts.array_fact, 2)'
        node = self._eval_expression(expression, node_id)
        self.assertEquals(node['facts']['array_fact'], [1])

        # verify removing from none returns none.  This is perhaps
        # questionable, but is inline with the rest of the none/empty
        # behavior.  It could probably also return [], but enforce
        # current behavior
        self._model_delete('facts', fact['id'])
        expression = 'facts.array_fact := remove(facts.array_fact, "test")'
        node = self._eval_expression(expression, node_id)
        self.assertEquals(node['facts']['array_fact'], None)

        # verify removing from a non-list raises SyntaxError
        self._model_create('facts', node_id=node_id,
                           key='array_fact', value='non-array')
        expression = 'facts.array_fact := remove(facts.array_fact, "whoops")'

        self.assertRaises(SyntaxError, self._eval_expression,
                          expression, node_id)

    def test_eval_namespaces(self):
        node_id = self.nodes['node-1']['id']
        expression = "facts.parent_id := value"
        ns = {"value": self.nodes['container']['id']}

        node = self._eval_expression(expression, node_id, ns)
        self.assertEquals(node['facts'].get('parent_id', None),
                          self.nodes['container']['id'])

    # test the inverter and regularizer functions
    def test_regularize_expression(self):
        expression = 'foo=value'
        regular = ast.regularize_expression(expression)
        self.logger.debug('Got regularized expression "%s" for "%s"' %
                          (regular, expression))
        self.assertEquals(regular, 'foo = value')

    def test_inverted_expression(self):
        expression = 'foo=value'
        inverted = ast.invert_expression(expression)
        self.logger.debug('Got inverted expression "%s" for "%s"' %
                          (inverted, expression))
        self.assertEquals(len(inverted), 1)
        self.assertEquals(inverted[0], 'foo := value')

    def test_inverted_union(self):
        expression = 'facts.test := union(facts.test, test)'
        inverted = ast.invert_expression(expression)
        self.logger.debug('Got inverted expression "%s" for "%s"' %
                          (inverted, expression))
        self.assertEquals(len(inverted), 1)
        self.assertEquals(inverted[0], 'test in facts.test')

    def test_inverted_remove(self):
        expression = 'facts.test := remove(facts.test, test)'
        inverted = ast.invert_expression(expression)
        self.logger.debug('Got inverted expression "%s" for "%s"' %
                          (inverted, expression))
        self.assertEquals(len(inverted), 1)
        self.assertEquals(inverted[0], 'test !in facts.test')

    def test_concrete_expression(self):
        expression = "foo = value"
        ns = {"value": 3}
        concrete = ast.concrete_expression(expression, ns)
        self.logger.debug('Got concrete expression "%s" for "%s"' %
                          (concrete, expression))
        # TODO(rpedde): This does not work like you think it does
        # self.assertTrue('foo = 3', concrete)
        # Using an assertEquals of the above fails
        # self.assertEquals(concrete, 'foo = 3')
        # But this works
        self.assertEquals(concrete, 'foo = value')

    def test_apply_expression(self):
        expression = 'facts.test := union(facts.test, "test")'

        node = self._model_get_by_id('nodes', self.nodes['node-1']['id'])

        # make sure we are applying into an empty fact
        self.assertFalse('test' in node['facts'])
        ast.apply_expression(self.nodes['node-1']['id'], expression, api)

        node = self._model_get_by_id('nodes', self.nodes['node-1']['id'])

        self.assertTrue('test' in node['facts'])
        self.assertEquals(node['facts']['test'], ['test'])

    # FIXME: when we get types
    def test_util_nth_with_none(self):
        expression = 'nth(0, facts.test)'  # nth of none?
        res = self._simple_expression(expression)
        self.assertIsNone(res)

    # FIXME: when we get types
    def test_util_nth_not_integer(self):
        expression = 'nth("a", facts.test)'  # raise with type error?
        res = self._simple_expression(expression)
        self.assertIsNone(res)

    # FIXME: when we get types
    def test_util_nth_index_out_of_range(self):
        self._model_create('facts', node_id=self.nodes['node-1']['id'],
                           key='test', value=[1, 2, 3])

        self.assertTrue(self._simple_expression('nth(2, facts.test)') is 3)
        self.assertIsNone(self._simple_expression('nth(3, facts.test)'))

    # FIXME: when we get types
    def test_str_casting_none(self):
        # this should fail, too, I think
        self.assertIsNone(self._simple_expression('str(facts.test)'))

        self._model_create('facts', node_id=self.nodes['node-1']['id'],
                           key='test', value=[1, 2, 3])
        self.assertEquals(self._simple_expression('str(facts.test)'),
                          '[1, 2, 3]')

        self._model_create('facts', node_id=self.nodes['node-1']['id'],
                           key='test', value=1)
        self.assertEquals(self._simple_expression('str(facts.test)'), '1')
