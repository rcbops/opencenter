#
# This tests that we can't reparent items to places where
# they don't make sense, or result in broken system.
# In addition, it tests the attrs.locked behavior to
# ensure things are locked that should be locked, etc.
#
# This gives the ui hints about what things should be
# drop targets, or dragable, etc.
#

import json

from util import ScaffoldedTestCase
from opencenter.db import api as db_api

import opencenter.backends


class BadStateTestCase(ScaffoldedTestCase):
    def setUp(self):
        self.nodes = {}
        self.tasks = {}
        self.api = db_api.api_from_models()

        # set up a couple nodes
        self.nodes['client-01'] = self._stub_node(
            'client-01',
            facts={'backends': ['agent', 'node'], 'parent_id': 2},
            attrs={
                'opencenter_agent_actions': {
                    'install_chef': {
                        'args': {},
                        'consequences': ['facts.backends := '
                                         'union(facts.backends,'
                                         '"chef-client")'],
                        'constraints': []}}})

        self.nodes['client-02'] = self._stub_node(
            'client-02',
            facts={'backends': ['agent', 'node'], 'parent_id': 2},
            attrs={
                'opencenter_agent_actions': {
                    'install_chef': {
                        'args': {},
                        'consequences': ['facts.backends := '
                                         'union(facts.backends,'
                                         '"chef-client")'],
                        'constraints': []}}})

        self.nodes['client-03'] = self._stub_node(
            'client-03',
            facts={'backends': ['agent', 'node'], 'parent_id': 2},
            attrs={
                'opencenter_agent_actions': {
                    'install_chef': {
                        'args': {},
                        'consequences': ['facts.backends := '
                                         'union(facts.backends,'
                                         '"chef-client")'],
                        'constraints': []}}})

        self.nodes['client-04'] = self._stub_node(
            'client-04',
            facts={'backends': ['agent', 'node'], 'parent_id': 2},
            attrs={
                'opencenter_agent_actions': {
                    'install_chef': {
                        'args': {},
                        'consequences': ['facts.backends := '
                                         'union(facts.backends,'
                                         '"chef-client")'],
                        'constraints': []}}})

        self.nodes['chef-server'] = self._stub_node(
            'chef-server',
            facts={'backends': ['agent', 'node'], 'parent_id': 2},
            attrs={
                'opencenter_agent_actions': {
                    'install_chef_server': {
                        'args': {},
                        'consequences': [],
                        'constraints': []},
                    'download_cookbooks': {
                        'args': {},
                        'consequences': [],
                        'constraints': []}}})

        self.nodes['adventurator'] = self._stub_node(
            'adventurator',
            facts={'backends': ['agent', 'node'], 'parent_id': 3},
            attrs={'opencenter_agent_output_modules': ['adventurator']})

    def _model_find_by_name(self, model, name):
        res = self._model_filter(model,
                                 'name = "%s"' % name)
        self.assertEqual(len(res), 1)
        return res[0]

    def _safely_run_plan(self, plan, node_id, expect_backend_fail=False):
        node = self._model_get_by_id('nodes', node_id)

        api = self.api

        if expect_backend_fail is True:
            api = db_api.ephemeral_api_from_api(self.api)

        self.logger.debug('applying plan: %s' % plan)

        for step in plan:
            primitive = step['primitive']

            ns = {}
            if 'ns' in step:
                ns = step['ns']

            self.logger.debug('safe-running primitive %s' % primitive)

            if not '.' in primitive:
                # is a run_task... see if there are any consequences
                actions = node['attrs'].get('opencenter_agent_actions', {})
                if primitive in actions:
                    consequences = actions[primitive].get('consequences', [])
                    for consequence in consequences:
                        concrete_expression = self.api.concrete_expression(
                            consequence, ns)
                        api.apply_expression(node_id,
                                             concrete_expression)

                pass
            else:
                if primitive != 'chef-client.converge_chef':
                    f = opencenter.backends.primitive_by_name(primitive)
                    result = f({}, api, node_id, **ns)

                    self.assertTrue('result_code' in result)

                    if expect_backend_fail is False:
                        self.logger.debug(result['result_str'])
                        self.assertEqual(result['result_code'], 0)
                    else:
                        if result['result_code'] != 0:
                            return

        if expect_backend_fail:
            raise AssertionError('Backend did not fail as expected')

    def _default_plan(self, plan, exceptions=None):
        if exceptions is None:
            exceptions = {}

        for step in plan:
            if 'args' in step:
                for arg in step['args']:
                    self.logger.debug('processing arg %s' % arg)
                    if arg in exceptions:
                        step['args'][arg]['value'] = exceptions[arg]
                    else:
                        self.assertTrue('default' in step['args'][arg])
                        step['args'][arg]['value'] = \
                            step['args'][arg]['default']
        return plan

    def _default_by_analysis(self, node_id, plan, exceptions=None):
        # this may not work for primitives that must have
        # coerced stuff...
        if exceptions is None:
            exceptions = {}

        node = self._model_get_by_id('nodes', node_id)

        new_plan = []
        for step in plan:
            new_plan_step = {'primitive': step['primitive'],
                             'ns': {}}
            # we've got the shape of it... now grab all the args
            # and default
            primitive = step['primitive']
            if not '.' in primitive:
                # it's a run_task... see if we can find it
                actions = node['attrs'].get('opencenter_agent_actions', {})

                if primitive in actions:
                    prim = actions[primitive]
                    for arg in prim['args']:
                        if arg in exceptions:
                            new_plan_step['ns'][arg] = exceptions[arg]
                        elif 'default' in prim['args'][arg]:
                            new_plan_step['ns'][arg] = \
                                prim['args'][arg]['default']
            new_plan.append(new_plan_step)

        return new_plan

    def _execute_adventure(self, name, node_id, expect_code=202,
                           exceptions=None, solve=True,
                           expect_backend_fail=False):
        adv = self._model_find_by_name('adventures', name)
        if solve is True:
            resp = self.client.post(
                '/adventures/%s/execute' % (adv['id'],),
                content_type='application/json',
                data=json.dumps({'node': node_id}))

            self.assertEqual(expect_code, resp.status_code)
            data = json.loads(resp.data)
            self.assertTrue(expect_code in [202, 403, 409])
            self.assertTrue('plan' in data)
            plan = data['plan']

            if resp.status_code == 409:
                plan = self._default_plan(plan, exceptions)

            self._post_and_run_plan(plan, node_id,
                                    expect_backend_fail=expect_backend_fail)
        else:
            plan = adv['dsl']
            plan = self._default_by_analysis(node_id, plan, exceptions)
            self._safely_run_plan(plan, node_id,
                                  expect_backend_fail=expect_backend_fail)

    def _post_and_run_plan(self, plan, node_id, expect_backend_fail=False):
        self.logger.debug('Reposting plan: %s' % plan)

        resp = self.client.post(
            '/plan/', content_type='application/json',
            data=json.dumps({'node': node_id,
                             'plan': plan}))

        self.assertEqual(resp.status_code, 202)
        data = json.loads(resp.data)

        self.assertTrue('plan' in data)
        plan = data['plan']

        # assert we have an adventurator task for this
        self.assertTrue('task' in data)

        # whack the task...
        self._model_delete('tasks', data['task']['id'])

        # ...and roll the plan forward
        self.logger.debug("Rolling plan forward....")
        self._safely_run_plan(plan, node_id,
                              expect_backend_fail=expect_backend_fail)

    def _verify_expression(self, node_id, expression, is_what=True):
        self.assertEqual(self.api.apply_expression(node_id, expression),
                         is_what)

    def _setup_cluster(self, solve=False):
        self._execute_adventure('Install Chef Server',
                                self.nodes['chef-server']['id'],
                                solve=solve)

        # verify node has moved to support
        self._verify_expression(self.nodes['chef-server']['id'],
                                'facts.parent_id = 3')

        # verify node is locked
        self._verify_expression(self.nodes['chef-server']['id'],
                                'attrs.locked = true')

        # some chef facts are artifacts of the run_task,
        # so we'll stub these.
        self._model_create('facts', node_id=self.nodes['chef-server']['id'],
                           key='chef_server_uri', value='http://blah')

        self._model_create('facts', node_id=self.nodes['chef-server']['id'],
                           key='chef_server_pem', value='0xDEADBEEF')

        self._execute_adventure('Create Nova Cluster', 1,
                                expect_code=409, solve=solve)

        # verify we now have a node named 'NovaCluster'
        self.logger.debug('All nodes: %s' % [x['name'] for x in
                                             self._model_get_all('nodes')])

        nc = self._model_find_by_name('nodes', 'NovaCluster')
        self.assertTrue('container' in nc['facts']['backends'])

        # verify it is locked
        self._verify_expression(nc['id'],
                                'attrs.locked = true')

        # verify we have a locked compute container
        cc = self._model_find_by_name('nodes', 'Compute')
        self.assertEqual(nc['id'], cc['facts']['parent_id'])
        self.assertTrue('container' in cc['facts']['backends'])

        self._verify_expression(cc['id'],
                                'attrs.locked = true')

    def _drag_node(self, what_node, what_container, expect_code=202,
                   exceptions=None):
        node_id = what_node
        parent_id = what_container

        if isinstance(what_node, str):
            node_id = self._model_find_by_name('nodes', what_node)['id']

        if isinstance(what_container, str):
            parent_id = self._model_find_by_name('nodes', what_container)['id']

        data = self._model_create('facts', node_id=node_id,
                                  key='parent_id', value=parent_id,
                                  please=True, raw=True,
                                  expect_code=expect_code)

        if expect_code == 403:
            # we expected it to fail, and it did
            return

        # if a 202, then grab the plan and run it.
        if expect_code == 202:
            plan = data['plan']
            self._safely_run_plan(plan, node_id)

        if expect_code == 409:
            plan = self._default_plan(plan, exceptions)
            self._post_and_run_plan(plan, node_id)

    def tearDown(self):
        # if you want something torn down, add it to self.nodes, self.tasks,
        # etc, and it will get automatically torn down.
        self._delete_items(dict([(x, [y['id'] for y in
                                      getattr(self, x, {}).values()])
                                 for x in ['nodes', 'tasks']]))

    def test_cluster(self):
        self._setup_cluster(solve=True)

        # verify that making a new cluster with same name fails
        # this is a little odd in that it solves okay, but
        # fails on the backend.
        self._execute_adventure('Create Nova Cluster', 1,
                                expect_code=409, solve=True,
                                expect_backend_fail=True)

        # verify no crazy cluster name
        self._execute_adventure('Create Nova Cluster', 1,
                                expect_code=409, solve=True,
                                expect_backend_fail=True,
                                exceptions={'cluster_name': '#&!@'})

        # verify we can't make an AZ with the same name as
        # the existing AZ.
        cc = self._model_find_by_name('nodes', 'Compute')
        self._execute_adventure('Create Availability Zone', cc['id'],
                                expect_code=409, solve=True,
                                expect_backend_fail=True,
                                exceptions={'az_name': 'nova'})

        # make sure we *can* create an AZ
        self._execute_adventure('Create Availability Zone', cc['id'],
                                expect_code=409, solve=True,
                                exceptions={'az_name': 'nova2'})

        self._model_find_by_name('nodes', 'AZ nova2')

        self._drag_node('chef-server', 'NovaCluster',
                        expect_code=403)

        self._drag_node('client-01', 'support',
                        expect_code=403)

        self._drag_node('chef-server', 'Infrastructure',
                        expect_code=403)

        # verify the unprovisioned container is locked
        up = self._model_find_by_name('nodes', 'unprovisioned')
        self._verify_expression(up['id'],
                                'attrs.locked = true')

        # FIXME: not working right now
        # self._drag_node('client-03', 'AZ nova',
        #                 expect_code=403)

        self._drag_node('client-01', 'Infrastructure')

        # make sure it really got rolled in
        ic = self._model_find_by_name('nodes', 'Infrastructure')
        x = self._model_get_by_id('nodes', self.nodes['client-01']['id'])

        self.logger.debug(x)

        self._verify_expression(self.nodes['client-01']['id'],
                                'attrs.locked = true')
        self._verify_expression(self.nodes['client-01']['id'],
                                'facts.parent_id = %s' % ic['id'])
        self._verify_expression(self.nodes['client-01']['id'],
                                'facts.nova_role = "nova-controller-master"')

        # make sure we can't pull the node into compute or something
        self._drag_node('client-01', 'AZ nova',
                        expect_code=403)
