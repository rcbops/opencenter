#

from util import RoushTestCase

import roush.db.api as db_api
from roush.webapp import ast


api = db_api.api_from_models()


class ExpressionTestCase(RoushTestCase):
    def setUp(self):
        self.nodes = {}
        self.interfaces = {}

        self.nodes['node-1'] = self._model_create('node', name='node-1')
        self.interfaces['chef'] = self._model_create('filter', name='chef',
                                                     filter_type='interface',
                                                     expr='facts.x = true')

    def tearDown(self):
        self._clean_all()

    def _run_expression(self, node, expression, ns={}):
        builder = ast.FilterBuilder(ast.FilterTokenizer(), expression,
                                    api=api)
        root_node = builder.build()
        return root_node.eval_node(node, symbol_table=ns)

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
        self._model_create('fact', node_id=self.nodes['node-1']['id'],
                           key='x', value=True)
        result = self._run_expression(self.nodes['node-1'], expression)
        self.logger.debug('Got result: %s' % result)
        self.assertEquals(result, True)

    def test_invert_equlas(self):
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
        self.assertTrue(len(result) == 1)

    def test_eval_assign(self):
        node_id = self.nodes['node-1']['id']
        expression = "parent_id := 3"

        node = self._eval_expression(expression, node_id)
        self.assertTrue(node['parent_id'] == 3)

    def test_eval_union(self):
        node_id = self.nodes['node-1']['id']
        expression = "facts.woof := union(facts.woof, 3)"

        node = self._eval_expression(expression, node_id)
        self.assertTrue(node['facts']['woof'] == [3])

    def test_eval_namespaces(self):
        node_id = self.nodes['node-1']['id']
        expression = "parent_id := value"
        ns = {"value": 3}

        node = self._eval_expression(expression, node_id, ns)
        self.assertTrue(node['parent_id'] == 3)

    # test the inverter and regularizer functions
    def test_regularize_expression(self):
        expression = 'foo=value'
        regular = ast.regularize_expression(expression)
        self.logger.debug('Got regularized expression "%s" for "%s"' %
                          (regular, expression))
        self.assertTrue('foo = value' == regular)

    def test_inverted_expression(self):
        expression = 'foo=value'
        inverted = ast.invert_expression(expression)
        self.logger.debug('Got inverted expression "%s" for "%s"' %
                          (inverted, expression))
        self.assertTrue(len(inverted) == 1)
        self.assertTrue('foo := value' == inverted[0])

    def test_inverted_union(self):
        expression = 'facts.test := union(facts.test, test)'
        inverted = ast.invert_expression(expression)
        self.logger.debug('Got inverted expression "%s" for "%s"' %
                          (inverted, expression))
        self.assertTrue(len(inverted) == 1)
        self.assertTrue('test in facts.test' == inverted[0])

    def test_concrete_expression(self):
        expression = "foo = value"
        ns = {"value": 3}
        concrete = ast.concrete_expression(expression, ns)
        self.logger.debug('Got concrete expression "%s" for "%s"' %
                          (concrete, expression))
        self.assertTrue('foo = 3', concrete)
