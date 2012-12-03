#

import copy

from util import RoushTestCase
from roush.webapp import ast
from roush.webapp import solver
from roush.db import api as db_api


api = db_api.api_from_models()


class SolverTestCase(RoushTestCase):
    def setUp(self):
        self._clean_all()

        self.nodes = {}
        self.interfaces = {}

        self.nodes['node-1'] = self._model_create('node', name='node-1')
        self.interfaces['chef'] = self._model_create('filter', name='chef',
                                                     filter_type='interface',
                                                     expr='facts.x = true')

    def tearDown(self):
        self._clean_all()

    def test_no_solution(self):
        self._clean_table('primitive')
        test_solver = solver.Solver(api, self.nodes['node-1']['id'],
                                    ['facts.x = true'])

        solvable, requires_input, path = test_solver.solve()
        self.logger.debug('Result of solve: %s' % path)
        self.assertFalse(solvable)

    # def test_implied_backend(self):
    #     test_solver = solver.Solver(api, self.nodes['node-1']['id'],
    #                                 ['facts.ostype = "booger"'])

    #     solvable, requires_input, path = test_solver.solve()
    #     self.logger.debug('Result of solve: %s' % path)
    #     self.assertTrue(solvable)
    #     self.assertTrue(path[0]['primitive']['name'] == 'node.set_fact')
    #     self.assertTrue(path[0]['args']['key'] == 'ostype')
    #     self.assertTrue(path[0]['args']['value'] == 'booger')

    # def test_multi_step(self):
    #     test_node = copy.deepcopy(self.nodes['node-1'])
    #     self._model_create('primitive', name='set_fact', args={},
    #                        constraints=[],
    #                        consequences=['facts.{x} := "{y}"'])
    #     solver = ast.Solver(test_node, None,
    #                         ['facts.x = "blah"',
    #                          'facts.y = "woof"'])
    #     solvable, requires_input, path = solver.solve()
    #     self.logger.debug('Result of solve: %s' % path)
    #     self.assertTrue(solvable)
    #     self.assertTrue(len(path) == 2)
    #     self.assertTrue(path[0]['primitive']['name'] == 'set_fact')
    #     self.assertTrue(path[1]['primitive']['name'] == 'set_fact')
