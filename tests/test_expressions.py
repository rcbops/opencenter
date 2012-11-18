#

from util import RoushTestCase

from roush.webapp import ast


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
        builder = ast.FilterBuilder(ast.FilterTokenizer(), expression)
        root_node = builder.build()
        return root_node.eval_node(node, symbol_table=ns)

    def _invert_expression(self, expression, ns={}):
        builder = ast.FilterBuilder(ast.FilterTokenizer(), expression)
        root_node = builder.build()
        return root_node.invert()

    def _eval_expression(self, expression, node, ns={}):
        builder = ast.FilterBuilder(ast.FilterTokenizer(), expression)
        return builder.eval_node(node, symbol_table=ns)

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
        expression = "foo := 3"
        test_node = {}
        self._eval_expression(expression, test_node)
        self.assertTrue(test_node['foo'] == 3)
        self.assertTrue(len(test_node) == 1)

    def test_eval_union(self):
        expression = "foo := union(foo, 3)"
        test_node = {}
        self._eval_expression(expression, test_node)
        self.assertTrue(test_node['foo'] == [3])
        self.assertTrue(len(test_node) == 1)

    def test_eval_namespaces(self):
        expression = "foo := value"
        test_node = {}
        ns = {"value": 3}
        self._eval_expression(expression, test_node, ns)
        self.assertTrue(test_node['foo'] == 3)
        self.assertTrue(len(test_node) == 1)
