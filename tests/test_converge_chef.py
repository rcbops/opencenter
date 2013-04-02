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
from mock import Mock, patch
from util import OpenCenterTestCase


class ConvergeChefTests(OpenCenterTestCase):
    def setUp(self):
        # load the backend
        self.backend = __import__(
            'opencenter.backends.chef-client',
            fromlist=['ChefClientBackend']).ChefClientBackend()

        # mock pychef api
        self.chef_api = Mock(name='ChefAPI')

        # mock Chef Environment from pychef
        self.chef_environment = Mock(name='Chef Environment',
                                     override_attributes={})

        # fake chef server oc node
        self.chef_server_node = {
            'facts': {
                'chef_server_uri': 'http://localhost',
                'chef_server_client_name': 'client_name',
                'chef_server_client_pem': 'client_pem'
            }
        }

        # fake oc node
        self.node = {
            'name': 'test',
            'facts': {
                'chef_server_consumed': 1,
                'chef_environment': '_default',
                'nova_role': ''
            }
        }

        # mock Chef Node from pychef
        self.chef_node = Mock(name='Chef Node', normal={}, run_list=[])

        # mock adventurator oc node
        self.adventurator = Mock(name='Adventurator')

        # mock oc API
        self.api = Mock(name='API')
        # return node, then chef server node by default
        self.api._model_get_by_id = Mock(
            side_effect=[self.node, self.chef_server_node])

        # calculated node/env attributes from templates
        self.node_attributes = {}
        self.environment_attributes = {}

        # stub out backend protected methods for full success case
        self.backend._get_nodes_in_env = Mock(return_value=[])
        self.backend._get_adventurator = Mock(return_value=self.adventurator)
        self.backend._find_or_create_environment = Mock(
            return_value=self.chef_environment)
        self.backend._get_chef_api = self.chef_api
        self.backend._get_node = Mock(return_value=self.chef_node)
        self.backend._node_exists = Mock(return_value=True)
        self.backend._remove_node = Mock(name='_remove_node')
        self.backend._represent_node_attributes = Mock(
            '_represent_node_attributes',
            return_value=[self.node_attributes, self.environment_attributes])
        self.backend._watch_converge_task = Mock(
            return_value=[True, 'success'])

    def tearDown(self):
        self.backend = None

    def test_fail_node_not_found(self):
        self.api._model_get_by_id = Mock(return_value=None)

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'cannot find node 1', 1)

    def test_fail_no_consumed_chef_fact(self):
        del self.node['facts']['chef_server_consumed']
        self.api._model_get_by_id = Mock(return_value=self.node)

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(
            result, 'missing fact: chef_server_consumed', 1)

    def test_fail_consumed_chef_not_found(self):
        self.api._model_get_by_id = Mock(side_effect=[self.node, None])

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'cannot find consumed chef server', 1)

    def test_fail_consumed_chef_missing_attributes(self):
        self.chef_server_node['facts'] = {}

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'chef server missing chef attrs', 1)

    def test_missing_environment_removes_node_from_chef(self):
        del self.node['facts']['chef_environment']

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.backend._remove_node.assert_called_with('test', self.chef_api())

    def test_fail_no_chef_environment(self):
        self.backend._find_or_create_environment = Mock(return_value=None)

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(
            result, 'Cannot find/create chef environment _default', 1)

    @patch('time.sleep')
    def test_fail_chef_node_register_timeout(self, mock_sleep):
        self.backend._node_exists = Mock(return_value=None)

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertEqual(mock_sleep.call_count, 11)
        self.assertFailResponse(
            result,
            "Node 'test' is not registered to chef.  Exceeded max retries", 1)

    def test_fail_adventurator_not_found(self):
        self.backend._get_adventurator = Mock(return_value=None)

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'could not find adventurator', 1)

    def test_sets_chef_node_environment_from_node_fact(self):
        self.chef_node.chef_environment = '_default'
        self.node['facts']['chef_environment'] = 'production'

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual(
            self.chef_node.chef_environment,
            self.node['facts']['chef_environment'])
        self.assertTrue(self.chef_node.save.called)

    def test_sets_chef_environment_from_cluster_attributes(self):
        self.chef_environment.override_attributes['thing'] = 'original'
        self.environment_attributes['thing'] = 'updated'

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual(
            self.chef_environment.override_attributes,
            self.environment_attributes)
        self.assertTrue(self.chef_environment.save.called)

    def test_fails_chef_environment_converge_unsuccessful(self):
        self.chef_environment.override_attributes['thing'] = 'original'
        self.environment_attributes['thing'] = 'updated'

        self.backend._watch_converge_task = Mock(
            return_value=[False, 'failed'])

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'First env pass: failed', 1)

    def test_sets_run_list_from_nova_role(self):
        self.node['facts']['nova_role'] = 'nova-compute'

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual(self.chef_node.run_list, ['role[single-compute]'])

    def test_merges_node_run_list_with_nova_role(self):
        self.chef_node.run_list = ['recipe[keeper]']
        self.node['facts']['nova_role'] = 'nova-compute'

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual(self.chef_node.run_list,
                         ['role[single-compute]', 'recipe[keeper]'])

    def test_merges_node_attributes_with_nova_attributes(self):
        self.chef_node.normal = {
            'level1': 1,
            'level2': {'a': 1},
            'level3': {'d': {'e': 1}}
        }
        self.node_attributes['level1'] = 'updated'
        self.node_attributes['level2'] = {'b': 2}

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual(self.chef_node.normal, {
            'level1': 'updated',
            'level2': {'a': 1, 'b': 2},
            'level3': {'d': {'e': 1}}
        })

    def test_merges_environment_attributes_with_nova_attributes(self):
        self.chef_environment.override_attributes = {
            'level1': 1,
            'level2': {'a': 1},
            'level3': {'d': {'e': 1}}
        }
        self.environment_attributes['level1'] = 'updated'
        self.environment_attributes['level2'] = {'b': 2}

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual(self.chef_environment.override_attributes, {
            'level1': 'updated',
            'level2': {'a': 1, 'b': 2},
            'level3': {'d': {'e': 1}}
        })

    def test_skip_node_in_converged_environment(self):
        self.node['facts']['nova_role'] = 'nova-compute'

        nodelist = Mock(return_value=[1, 2])
        self.backend._get_nodes_in_env = nodelist

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual([2], nodelist())

    def test_fails_chef_node_converge_unsuccessful(self):
        self.node['facts']['nova_role'] = 'nova-compute'

        self.backend._watch_converge_task = Mock(
            return_value=[False, 'failed'])

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'First node pass: failed', 1)

    def test_fails_chef_node_environment_converge_unsuccessful(self):
        self.node['facts']['nova_role'] = 'nova-compute'

        self.backend._watch_converge_task = Mock(
            side_effect=[[True, 'success'], [False, 'failed']])

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'First env pass: failed', 1)

    def test_chef_node_attr_update_causes_converge(self):
        self.node_attributes['foo'] = 'bar'

        self.backend._watch_converge_task = Mock(
            side_effect=Exception('converge attempted'))

        self.assertRaisesRegexp(Exception, 'converge attempted',
                                self.backend.converge_chef, None, self.api, 1)

    def test_chef_env_attr_update_causes_converge(self):
        self.environment_attributes['foo'] = 'bar'

        self.backend._watch_converge_task = Mock(
            side_effect=Exception('converge attempted'))

        self.assertRaisesRegexp(Exception, 'converge attempted',
                                self.backend.converge_chef, None, self.api, 1)
