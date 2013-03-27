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

        # stub out backend protected methods for full success case
        self.backend._get_adventurator = Mock(return_value=self.adventurator)
        self.backend._find_or_create_environment = Mock(
            return_value=self.chef_environment)
        self.backend._get_chef_api = self.chef_api
        self.backend._get_node = Mock(return_value=self.chef_node)
        self.backend._node_exists = Mock(return_value=True)
        self.backend._remove_node = Mock(name='_remove_node')
        self.backend._represent_node_attributes = Mock(
            '_represent_node_attributes', return_value=[{}, {}])

        #self.c2 = self._model_create('nodes',
                                     #name=self._random_str())
        #self.c1 = self._model_create('nodes',
                                     #name=self._random_str())
        #self._model_create('facts',
                           #node_id=self.c1['id'],
                           #key='parent_id',
                           #value=self.c2['id'])
        #self.n1 = self._model_create('nodes',
                                     #name=self._random_str())
        #self._model_create('facts',
                           #node_id=self.n1['id'],
                           #key='parent_id',
                           #value=self.c1['id'])

    def tearDown(self):
        self.backend = None
        #c2_facts = self._model_filter('facts',
                                      #'node_id=%s' % self.c2['id'])

        #c1_facts = self._model_filter('facts',
                                      #'node_id=%s' % self.c1['id'])

        #n1_facts = self._model_filter('facts',
                                      #'node_id=%s' % self.n1['id'])

        #for fact_id in [x['id'] for x in c2_facts + c1_facts + n1_facts]:
            #self.app.logger.debug('deleting fact %s' % fact_id)
            #self._model_delete('facts', fact_id)

        #self._model_delete('nodes', self.n1['id'])
        #self._model_delete('nodes', self.c2['id'])
        #self._model_delete('nodes', self.c1['id'])

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
        self.backend._node_exists = Mock(side_effect=[False, False, False])

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertEqual(mock_sleep.call_count, 3)
        self.assertFailResponse(
            result,
            "Node 'test' is not registered to chef.  Exceeded max retries", 1)

    def test_fail_adventurator_not_found(self):
        self.backend._get_adventurator = Mock(return_value=None)

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertFailResponse(result, 'could not find adventurator', 1)

    def test_sets_chef_node_environment_from_node(self):
        self.chef_node.chef_environment = '_default'
        self.node['facts']['chef_environment'] = 'production'

        result = self.backend.converge_chef(None, self.api, 1)

        self.assertOkResponse(result)
        self.assertEqual(
            self.chef_node.chef_environment,
            self.node['facts']['chef_environment'])
        self.assertTrue(self.chef_node.save.called)
