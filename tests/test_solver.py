#

import copy
import json

from util import RoushTestCase
from roush.webapp import ast
from roush.webapp import solver
from roush.db import api as db_api

import roush.backends

api = db_api.api_from_models()


class SolverTestCase(RoushTestCase):
    def setUp(self):
        if roush.backends.primitive_by_name('test.set_test_fact') is None:
            roush.backends.load_specific_backend('tests.test', 'TestBackend')

        self._clean_all()

        self.interfaces = {}

        self.adv = self._model_create('nodes', name='adventurator')
        self._model_create('facts', node_id=self.adv['id'],
                           key='backends', value=['node', 'agent'])

        self.container = self._model_create('nodes', name='container')
        self._model_create('facts', node_id=self.container['id'],
                           key='backends', value=['node', 'container'])

        self.node = self._model_create('nodes', name='node-1')

        chef_expr = '(facts.chef_server_uri != None) and ' \
            '(facts.chef_server_pem != None)'

        # some of our current primitives require this
        self.interfaces['chef'] = self._model_create('filters',
                                                     name='chef-server',
                                                     filter_type='interface',
                                                     expr=chef_expr)

        self.api = db_api.api_from_models()

        self.assertTrue(len(self._model_get_all('tasks')) == 0)

    def tearDown(self):
        self._clean_all()

    def _make_adventurator(self):
        self._model_create('attrs', node_id=self.adv['id'],
                           key='roush_agent_output_modules',
                           value=['adventurator'])

    def _plan_includes(self, plan, primitive):
        return primitive in [x['primitive'] for x in plan]

    def _plan_entry(self, plan, primitive, nth=0):
        return [x for x in plan if x['primitive'] == primitive][nth]

    def _assert_task(self, plan, nth):
        tasks = self._model_get_all('tasks')

        self.assertTrue(len(tasks) > nth)

        task_plan = tasks[nth]['payload']['adventure_dsl']
        self.assertTrue(plan == task_plan)

    def _run_plan_safe(self, plan, node_id):
        # we'll run a plan, skipping those that are harmful
        # node.run_task, for example
        for step in plan:
            primitive = step['primitive']

            ns = {}
            if 'ns' in step:
                ns = step['ns']

            if 'run_task' in step:
                continue

            f = roush.backends.primitive_by_name(primitive)

            f(self.api, node_id, **ns)

    def test_no_adventurator(self):
        # trying to run any solved thing should fail
        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='parent_id',
                                  value=self.container['id'],
                                  please=True,
                                  raw=True, expect_code=403)

        # this is somewhat bogus... point is really that it should 403
        self.assertTrue(resp['message'] == 'no adventurator')

    def test_reparent(self):
        # make sure setting parent results in an unambiguous solve
        # with node.set_parent and a ns of parent=id
        #
        self._make_adventurator()

        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='parent_id',
                                  value=self.container['id'],
                                  please=True,
                                  raw=True, expect_code=202)

        self.assertTrue('plan' in resp)
        self.assertTrue(self._plan_includes(resp['plan'], 'node.set_parent'))

        entry = self._plan_entry(resp['plan'], 'node.set_parent')
        self.assertTrue('ns' in entry)
        self.assertTrue(str(entry['ns']['parent']) ==
                        str(self.container['id']))

        # we should have a task... make sure 0th task has same plan
        self._assert_task(resp['plan'], 0)

        # roll the task forward and make sure the actual consequence happens
        self._run_plan_safe(resp['plan'], self.node['id'])

        node = self._model_get_by_id('nodes', self.node['id'])
        self.assertTrue(str(node['facts']['parent_id']) ==
                        str(self.container['id']))

    def test_bogusfact(self):
        # make sure that setting a fact not present in the backend
        # results in a 403

        self._make_adventurator()

        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='bogus_value',
                                  value=self.container['id'],
                                  please=True,
                                  raw=True, expect_code=403)

    def test_implied_backend(self):
        self._make_adventurator()

        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='solved_fact',
                                  value='test_value',
                                  please=True,
                                  raw=True, expect_code=202)

        # make sure this is up to expectations
        self.assertTrue('plan' in resp)
        plan = resp['plan']

        self.assertTrue(self._plan_includes(plan, 'node.add_backend'))
        self.assertTrue(self._plan_includes(plan, 'node.set_fact'))

        # we should have a task... make sure 0th task has same plan
        self._assert_task(resp['plan'], 0)

        # roll the task forward and make sure the actual consequence happens
        self._run_plan_safe(resp['plan'], self.node['id'])

        node = self._model_get_by_id('nodes', self.node['id'])
        self.assertTrue(node['facts']['solved_fact'] == 'test_value')
        self.assertTrue('test' in node['facts']['backends'])

    def test_implied_backend(self):
        self._make_adventurator()

        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='solved_fact',
                                  value='test_value',
                                  please=True,
                                  raw=True, expect_code=202)

        # make sure this is up to expectations
        self.assertTrue('plan' in resp)
        plan = resp['plan']

        self.assertTrue(self._plan_includes(plan, 'node.add_backend'))
        self.assertTrue(self._plan_includes(plan, 'node.set_fact'))

        # we should have a task... make sure 0th task has same plan
        self._assert_task(resp['plan'], 0)

        # roll the task forward and make sure the actual consequence happens
        self._run_plan_safe(resp['plan'], self.node['id'])

        node = self._model_get_by_id('nodes', self.node['id'])
        self.assertTrue(node['facts']['solved_fact'] == 'test_value')
        self.assertTrue('test' in node['facts']['backends'])

        # try the same fact change and make sure we don't drag in
        # the backend now.

        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='solved_fact',
                                  value='test_value2',
                                  please=True,
                                  raw=True, expect_code=202)

        self.assertTrue('plan' in resp)
        plan = resp['plan']

        self.assertFalse(self._plan_includes(plan, 'node.add_backend'))

    def test_required_args(self):
        self._make_adventurator()

        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='unsettable_fact',
                                  value='blah',
                                  please=True,
                                  raw=True, expect_code=409)

        # make sure this is up to expectations
        self.assertTrue('plan' in resp)
        plan = resp['plan']

        self.assertTrue(self._plan_includes(plan, 'test.set_test_fact'))
        self.assertTrue(self._plan_includes(plan, 'node.add_backend'))

        # we should have a plan with args, as specified by test backend..
        entry = self._plan_entry(resp['plan'], 'test.set_test_fact')

        self.assertTrue('args' in entry)
        self.assertTrue('other_thing' in entry['args'])
        self.assertTrue(len(entry['args']) == 1)

        # here, we should pump in another thing.

    def test_nova_backend(self):
        # make sure adding a nova backend pulls in chef-client
        self._make_adventurator()

        # pop in a nova fact, which should pull in both
        # a nova backend and a chef-client backend
        resp = self._model_create('facts', node_id=self.node['id'],
                                  key='nova_az',
                                  value='nova',
                                  please=True,
                                  raw=True, expect_code=202)

        self.assertTrue('plan' in resp)
        plan = resp['plan']

        entry = self._plan_entry(plan, 'node.add_backend')
        self.assertTrue('ns' in entry)
        self.assertTrue('backend' in entry['ns'])
        self.assertTrue('chef-client' == entry['ns']['backend'])

    # after we get scaffolding by default
    # def test_install_chef_server(self):
    #     self._make_adventurator()

    #     resp = self.client.post('/adventures/3/execute',
    #                             content_type='application/json',
    #                             data={'node': self.node['id']})


    #     self.assertTrue(resp.status_code == 402)
