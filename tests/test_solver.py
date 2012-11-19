#

import copy

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

    def test_no_solution(self):
        test_node = copy.deepcopy(self.nodes['node-1'])
        solver = ast.Solver(test_node, None,
                            ['facts.x = true'])

        solvable, requires_input, path = solver.solve()
        self.logger.debug('Result of solve: %s' % path)
        self.assertFalse(solvable)

    def test_solution(self):
        test_node = copy.deepcopy(self.nodes['node-1'])
        self._model_create('primitive', name='set_fact', args={},
                           constraints=[],
                           consequences=['facts.{x} := "{y}"'])
        solver = ast.Solver(test_node, None,
                            ['facts.x = "blah"'])
        solvable, requires_input, path = solver.solve()
        self.logger.debug('Result of solve: %s' % path)
        self.assertTrue(solvable)
        self.assertTrue(path[0]['primitive']['name'] == 'set_fact')
        self.assertTrue(path[0]['args']['y'] == 'blah')
        self.assertTrue(path[0]['args']['x'] == 'x')

    def test_multi_step(self):
        test_node = copy.deepcopy(self.nodes['node-1'])
        self._model_create('primitive', name='set_fact', args={},
                           constraints=[],
                           consequences=['facts.{x} := "{y}"'])
        solver = ast.Solver(test_node, None,
                            ['facts.x = "blah"',
                             'facts.y = "woof"'])
        solvable, requires_input, path = solver.solve()
        self.logger.debug('Result of solve: %s' % path)
        self.assertTrue(solvable)
        self.assertTrue(len(path) == 2)
        self.assertTrue(path[0]['primitive']['name'] == 'set_fact')
        self.assertTrue(path[1]['primitive']['name'] == 'set_fact')
