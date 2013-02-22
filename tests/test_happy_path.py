import json

from util import ScaffoldedTestCase
from opencenter.db import api as db_api

import opencenter.backends


class HappyPathTestCase(ScaffoldedTestCase):
    def setUp(self):
        self.server = self._model_create('nodes', name='opencenter-server')
        self.agent = self._model_create('nodes', name='opencenter-client')

        for node_id in [self.server['id'], self.agent['id']]:
            self._make_facts(node_id,
                             {'parent_id': 2,
                              'backends': ['agent', 'node']})

        # grab the api so we can roll stuff forward
        self.api = db_api.api_from_models()

    def tearDown(self):
        self._clean_node(self.server['id'])
        self._clean_node(self.agent['id'])
        self._clean_table('tasks')

    def _clean_node(self, node_id):
        node_id = int(node_id)

        facts = self._model_filter('facts',
                                   'node_id=%d' % node_id)
        for fact in facts:
            self._model_delete('facts', fact['id'])

        attrs = self._model_filter('attrs',
                                   'node_id=%d' % node_id)
        for attr in attrs:
            self._model_delete('attrs', attr['id'])

        self._model_delete('nodes', node_id)

    def _plan_includes(self, plan, primitive):
        return primitive in [x['primitive'] for x in plan]

    def _plan_entry(self, plan, primitive, nth=0):
        return [x for x in plan if x['primitive'] == primitive][nth]

    def _safely_run_plan(self, plan, node_id):
        node = self.api._model_get_by_id('nodes', node_id)

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
                        self.api.apply_expression(node_id,
                                                  concrete_expression)

                pass
            else:
                f = opencenter.backends.primitive_by_name(primitive)
                f({}, self.api, node_id, **ns)

    def _make_facts(self, node_id, facts):
        for k, v in facts.items():
            self._model_create('facts', node_id=node_id,
                               key=k, value=v)

    def _make_chef_server(self):
        # dummy up the facts for a chef server
        self._make_facts(self.server['id'],
                         {'chef_server_uri': 'http://blahblah',
                          'chef_server_pem': 'pemitypempempem',
                          'chef_server_client_name': 'admin',
                          'chef_server_client_pem': 'pemitypempempem'})

    def _make_adventurator(self):
        self._model_create('attrs', node_id=self.server['id'],
                           key='opencenter_agent_output_modules',
                           value=['adventurator'])

    def _execute_adventure(self, adventure_id, node_id):
        adventure_id = int(adventure_id)

        self.logger.debug('running adventure %d' % adventure_id)

        resp = self.client.post(
            '/adventures/%d/execute' % (adventure_id),
            content_type='application/json',
            data=json.dumps({'node': node_id}))

        self.logger.debug('Result %d: %s' % (resp.status_code,
                                             resp.data))
        return json.loads(resp.data)

    def _valid_adventures(self, node_id):
        node_id = int(node_id)

        resp = self.client.get('/nodes/%d/adventures' % node_id)

        result = json.loads(resp.data)
        self.logger.debug('Result of adventures: %s' % result)

        valid_adventures = [x['id'] for x in result['adventures']]
        return valid_adventures

    def _default_plan(self, plan):
        for step in plan:
            if 'args' in step:
                for arg in step['args']:
                    self.assertTrue('default' in step['args'][arg])
                    step['args'][arg]['value'] = step['args'][arg]['default']
        return plan

    def _plan_submit(self, plan, node_id):
        node_id = int(node_id)

        self.logger.debug('running plan %s' % plan)

        resp = self.client.post(
            '/plan/', content_type='application/json',
            data=json.dumps({'node': node_id,
                             'plan': plan}))

        result = json.loads(resp.data)
        self.logger.debug('Result of plan submission: %s' % result)

        return result

    def test_install_chef_server_no_adventurator(self):
        agent_actions = json.loads("""
{
  "download_cookbooks": {
        "args": {"CHEF_SERVER_COOKBOOK_CHANNELS": {
                    "type": "evaluated",
                     "expression": "true"}},
        "consequences": [],
        "constraints": [],
        "timeout": 300
  },
  "install_chef_server": {
        "args": {},
        "consequences": [],
        "constraints": []
  }
}""")
        self._model_create(
            'attrs', node_id=self.server['id'],
            key='opencenter_agent_actions',
            value=agent_actions)

        chef_adventure = self._model_filter(
            'adventures', '"Chef Server" in name')

        self.assertEqual(len(chef_adventure), 1)
        chef_adventure = chef_adventure[0]['id']

        # make sure this is in server adventure list
        valid_adventures = self._valid_adventures(
            self.server['id'])
        self.assertTrue(chef_adventure in valid_adventures)

        result = self._execute_adventure(
            chef_adventure, self.server['id'])

        # this should fail, with no adventurator
        self.assertTrue('status' in result)
        self.assertEqual(result['status'], 403)

        # this is kind of fragile, as the result
        # format could change, but I want to know that it
        # failed as a result of not finding an adventurator,
        # so fragile it is
        self.assertTrue('message' in result)
        self.assertTrue('no adventurator' in result['message'])

    def test_install_chef_server(self):
        self._make_adventurator()
        agent_actions = json.loads("""
{
  "download_cookbooks": {
        "args": {"CHEF_SERVER_COOKBOOK_CHANNELS": {
                    "type": "evaluated",
                     "expression": "true"}},
        "consequences": [],
        "constraints": [],
        "timeout": 300
  },
  "install_chef_server": {
        "args": {},
        "consequences": [],
        "constraints": []
  }
}""")
        self._model_create(
            'attrs', node_id=self.server['id'],
            key='opencenter_agent_actions',
            value=agent_actions)

        chef_adventure = self._model_filter(
            'adventures', '"Chef Server" in name')

        self.assertEqual(len(chef_adventure), 1)
        chef_adventure = chef_adventure[0]['id']

        # make sure this is in server's adventure list
        valid_adventures = self._valid_adventures(
            self.server['id'])
        self.assertTrue(chef_adventure in valid_adventures)

        result = self._execute_adventure(
            chef_adventure, self.server['id'])

        self.assertTrue('status' in result)
        self.assertEqual(result['status'], 202)
        self.assertTrue('plan' in result)
        # we don't really care what the plan is -- it's
        # in the scaffolding.  We're good

    def test_make_nova_cluster(self):
        self._make_adventurator()

        nca = self._model_filter('adventures',
                                 '"Nova Cluster" in name')

        self.assertEqual(len(nca), 1)
        nca = nca[0]['id']

        # make sure this doesn't show up as valid adventure
        valid_adventures = self._valid_adventures(1)
        self.assertFalse(nca in valid_adventures)

        self._make_chef_server()

        # now, it _should_ show up
        valid_adventures = self._valid_adventures(1)
        self.assertTrue(nca in valid_adventures)

        result = self._execute_adventure(nca, 1)

        # this should 409
        self.assertTrue('status' in result)
        self.assertEqual(result['status'], 409)

        self.assertTrue('plan' in result)

        plan = result['plan']

        # now, fill in the plan with defaults and submit
        plan = self._default_plan(plan)

        result = self._plan_submit(plan, 1)

        self.assertTrue('status' in result)
        self.assertEqual(result['status'], 202)

        plan = result['plan']

        # roll the plan forward and make sure it does what we think
        node_count = len(self._model_get_all('nodes'))

        self._safely_run_plan(plan, 1)

        new_node_count = len(self._model_get_all('nodes'))

        # we should now have a nova cluster, infra, compute and az... 4 new
        # nodes.

        self.assertEqual(node_count + 4, new_node_count)

        agent_actions = json.loads("""
{
  "install_chef": {
    "args": {},
    "consequences": [
      "facts.backends := union(facts.backends, 'chef-client')"
    ],
    "constraints": [],
    "timeout": 300
  }
}""")

        # guess we should probably reparent now.
        self._model_create(
            'attrs', node_id=self.agent['id'],
            key='opencenter_agent_actions',
            value=agent_actions)

        infra_container = self._model_filter('nodes',
                                             '"frastructure" in name')

        self.assertEqual(len(infra_container), 1)
        infra_container = infra_container[0]['id']

        resp = self._model_create('facts', node_id=self.agent['id'],
                                  key='parent_id', value=infra_container,
                                  please=True, raw=True, expect_code=202)
