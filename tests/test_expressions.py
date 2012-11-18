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
