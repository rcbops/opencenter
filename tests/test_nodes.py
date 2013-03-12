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
import json
import random
import string
import unittest2

from opencenter.db.database import init_db
from opencenter import webapp

from util import OpenCenterTestCase, ScaffoldedTestCase


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


# class NodeRegister(unittest2.TestCase):
class NodeRegister(OpenCenterTestCase):
    def setUp(self):
        self.content_type = 'application/json'
        self.name = _randomStr(10)

    def tearDown(self):
        self._clean_all()

    def test_node_registration(self):
        data = {'hostname': self.name}
        resp = self.client.post('/nodes/whoami',
                                content_type=self.content_type,
                                data=json.dumps(data))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.logger.debug(out)
        self.assertEquals(out['node']['name'], self.name)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'success')

    def test_bad_node_registration(self):
        data = {'nothostname': self.name}
        resp = self.client.post('/nodes/whoami',
                                content_type=self.content_type,
                                data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.logger.debug(out)
        self.assertEquals(out['message'],
                          "'hostname' not found in json object")
        self.assertEquals(out['status'], 400)

# shep, i broke this.  sorry.  but I'm testing more than this in
# happypathtests, so we can argue over it tomorrow?  :)

# class NodeAdventures(ScaffoldedTestCase):
#     def setUp(self):
#         self.content_type = 'application/json'
#         self.name = _randomStr(10)

#     def tearDown(self):
#         pass

#     def test_check_for_install_chef_server_adventure(self):
#         data = {'hostname': self.name}
#         resp = self.client.post('/nodes/whoami',
#                                 content_type=self.content_type,
#                                 data=json.dumps(data))
#         self.assertEquals(resp.status_code, 200)
#         out = json.loads(resp.data)
#         new_node_id = out['node']['id']
#         resp = self.client.get('/nodes/%s/adventures' % new_node_id,
#                                content_type=self.content_type)
#         self.assertEquals(resp.status_code, 200)
#         out = json.loads(resp.data)
#         adventure_install_chef_server = False
#         for adv in out['adventures']:
#             if adv['name'] == "install chef server":
#                 adventure_install_chef_server = True
#         self.assertTrue(adventure_install_chef_server)


class NodeCreateTests(OpenCenterTestCase):
    def setUp(self):
        self.name = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {_randomStr(5): _randomStr(10),
                        _randomStr(5): {_randomStr(5): _randomStr(10)},
                        _randomStr(5): [_randomStr(10), _randomStr(10)]}
        self.content_type = 'application/json'
        self.clus1_name = _randomStr(10)
        self.clus1_desc = _randomStr(30)
        self.clus1_data = {'name': self.clus1_name,
                           'description': self.clus1_desc}

    def tearDown(self):
        self._clean_all()

    def _delete_node(self, node_id):
        resp = self.client.delete('/nodes/%s' % node_id,
                                  content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

    def test_create_node_with_name_only(self):
        data = {'name': self.name}
        resp = self.client.post('/nodes/',
                                content_type=self.content_type,
                                data=json.dumps(data))
        out = json.loads(resp.data)
        self.logger.debug(out)
        self.assertEquals(resp.status_code, 201)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Node Created')
        self.assertEquals(out['node']['name'], self.name)

    def test_create_node_without_name(self):
        data = {'description': self.desc}
        resp = self.client.post('/nodes/',
                                content_type=self.content_type,
                                data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)

    def _generic_test(self, method, path, code):
        resp = self.client.__getattribute__(method)(
            path,
            content_type=self.content_type)
        self.assertEquals(resp.status_code, code)


class NodeInvalidHTTPMethodTests(OpenCenterTestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _execute_method(self, method_name, path, http_code):
        """Helper function that will execute a method, against a path and
           verify the returned http code

        :param method_name: name of the http method to execute
        :param path: path to execute the http call against
        :param http_code: http error code to validate against
        """
        content_type = 'application/json'
        resp = self.client.__getattribute__(method_name)(
            path,
            content_type=content_type)
        self.assertEquals(resp.status_code, http_code)

    def test_405_returned_by_delete_on_nodes(self):
        self._execute_method('delete', '/nodes/', 405)

    def test_405_returned_by_patch_on_nodes(self):
        self._execute_method('patch', '/nodes/', 405)

    def test_405_returned_by_put_on_nodes(self):
        self._execute_method('put', '/nodes/', 405)

    def test_405_returned_by_post_on_nodes_with_id(self):
        self._execute_method('post', '/nodes/1', 405)

    def test_405_returned_by_patch_on_nodes_with_id(self):
        self._execute_method('patch', '/nodes/1', 405)


class NodeTransactionTests(OpenCenterTestCase):
    def setUp(self):
        self.container = self._model_create('nodes', name='test_container')
        self._model_create('facts', node_id=self.container['id'],
                           key='backends',
                           value='["container", "node"]')
        self.node = self._model_create('nodes', name='test-node-1')

        self.node_a = self._model_create('nodes', name='test-node-A')
        self.node_b = self._model_create('nodes', name='test-node-B')
        self.node_c = self._model_create('nodes', name='test-node-C')

    def tearDown(self):
        self._model_delete('nodes', self.container['id'])
        self._model_delete('nodes', self.node['id'])
        self._model_delete('nodes', self.node_a['id'])
        self._model_delete('nodes', self.node_b['id'])
        self._model_delete('nodes', self.node_c['id'])

    def _cleanup_nodes(self, node_list):
        """Cleans up nodes from the db

        node_list -- list of node objects to delete
        """
        for node in node_list:
            self._model_delete('nodes', node['id'])

    def _reparent_nodes(self, node_list, container_id):
        """Reparents a list of nodes under a container node

        node_list -- list of node objects
        container_id -- id to reparent nodes to
        """
        for node in node_list:
            self._model_create('facts', node_id=node['id'],
                               key='parent_id',
                               value=container_id)

    def test_query_latest_transaction(self):
        """test_query_latest_transaction

        Verify latest transaction payload

        Expected Result:

        'transaction': {
            'session_key': <random_string>,
            'txid': <trx_id>
        }
        """
        trans = self._get_txid()
        self.assertIsNotNone(trans['session_key'])
        self.assertTrue('txid' in trans)

    def test_verify_transaction_info_after_attr_update(self):
        """test_verify_transaction_info_after_attr_update

        Verify trans info after creating an attr on a node

        Expected Result: 'nodes' list containing only the single node_id
        """
        trans = self._get_txid()
        old_trans_id = trans['txid']
        session_key = trans['session_key']

        # Add a new attr to node
        self._model_create('attrs', node_id=self.node['id'],
                           key=_randomStr(5),
                           value=_randomStr(10))

        txinfo, changed_nodes = self._model_get_updates('nodes', session_key,
                                                        old_trans_id)
        self.assertTrue(txinfo['txid'] != old_trans_id)
        self.assertEquals(txinfo['session_key'], session_key)
        self.assertEquals(changed_nodes, [self.node['id']])

    def test_verify_trans_info_after_reparenting_three_nodes(self):
        """test_verify_trans_info_after_reparenting_three_nodes

        Verify transaction information after reparenting three nodes
        under a container

        Expected Result: 'nodes' list containing the three node_ids
        """
        test_container = self._model_create('nodes', name=_randomStr(15))
        self._model_create('facts', node_id=test_container['id'],
                           key='backends',
                           value='["node", "container"]')

        # Grab starting point info
        trans = self._get_txid()
        old_trans_id = trans['txid']
        session_key = trans['session_key']

        # Reparent nodes under container
        self._reparent_nodes(
            [self.node_a, self.node_b, self.node_c], test_container['id'])

        # Now lets look at updates from old_trans_id to latest
        trans, changed_nodes = self._model_get_updates('nodes', session_key,
                                                       old_trans_id)

        self.assertEquals(trans['session_key'], session_key)
        self.assertNotEquals(trans['txid'], old_trans_id)
        self.assertEquals(set(changed_nodes), set([self.node_a['id'],
                                                   self.node_b['id'],
                                                   self.node_c['id']]))

    def test_trans_info_inheritance(self):
        test_container = self._model_create('nodes', name=_randomStr(15))

        # Reparent nodes under container
        self._reparent_nodes(
            [self.node_a, self.node_b, self.node_c], test_container['id'])

        # Grab starting point info
        trans = self._get_txid()
        old_trans_id = trans['txid']
        session_key = trans['session_key']

        # Lets set a fact on the container
        self._model_create('facts', node_id=test_container['id'],
                           key='backends',
                           value='["node", "container", "agent"]')

        # Now lets look at updates from old_trans_id to latest
        trans, changed_nodes = self._model_get_updates('nodes', session_key,
                                                       old_trans_id)

        self.assertEquals(trans['session_key'], session_key)
        test_id_list = [test_container['id'],
                        self.node_a['id'],
                        self.node_b['id'],
                        self.node_c['id']]
        self.assertEquals(set(changed_nodes), set(test_id_list))

    def test_bad_session_key(self):
        trans = self._get_txid()
        _ = self._model_get_updates('nodes', 'xxx', trans['txid'],
                                    expect_code=410, raw=True)

    def test_bad_txid(self):
        trans = self._get_txid()
        _, _ = self._model_get_updates('nodes', trans['session_key'],
                                       0, expect_code=410, raw=True)

    def test_delete_node_updates_transactions(self):
        my_node = self._model_create('nodes', name='delete_me')

        # Grab starting point info
        trans = self._get_txid()
        old_trans_id = trans['txid']
        session_key = trans['session_key']

        trans, changed_nodes = self._model_get_updates('nodes', session_key,
                                                       old_trans_id)
        self.assertEquals(set(changed_nodes), set())

        self._model_delete('nodes', my_node['id'])

        # Now lets look at updates from old_trans_id to latest
        trans, changed_nodes = self._model_get_updates('nodes', session_key,
                                                       old_trans_id)

        self.assertEquals(trans['session_key'], session_key)
        self.assertEquals(set(changed_nodes), set([my_node['id']]))

class NodeMiscTests(OpenCenterTestCase):
    def test_cascading_deletes(self):
        new_node = self._model_create('nodes', name='test1')
        new_fact = self._model_create('facts',
                                      node_id=new_node['id'],
                                      key='test1',
                                      value='x')
        new_attr = self._model_create('attrs',
                                      node_id=new_node['id'],
                                      key='test1',
                                      value='y')

        expanded_node = self._model_get_by_id('nodes', new_node['id'])
        self.assertTrue('test1' in expanded_node['facts'])
        self.assertTrue('test1' in expanded_node['attrs'])
        self.assertEqual(expanded_node['facts']['test1'], 'x')
        self.assertEqual(expanded_node['attrs']['test1'], 'y')

        self._model_delete('nodes', new_node['id'])

        # now, we make sure that the fact has been deleted
        # this will assert unless we get a 404.
        self._model_get_by_id('facts', new_fact['id'],
                              expect_code=404, raw=True)

        self._model_get_by_id('attrs', new_fact['id'],
                              expect_code=404, raw=True)
        
