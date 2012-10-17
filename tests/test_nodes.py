# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import string
import time
import unittest2

from db.database import init_db
import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class NodeCreateTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.hostname = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {_randomStr(5): _randomStr(10),
                        _randomStr(5): {_randomStr(5): _randomStr(10)},
                        _randomStr(5): [_randomStr(10), _randomStr(10)]}
        self.content_type = 'application/json'
        # need to create a test cluster
        self.clus1_name = _randomStr(10)
        self.clus1_desc = _randomStr(30)
        self.clus1_config = {_randomStr(10): _randomStr(20)}
        self.clus1_data = {'name': self.clus1_name,
                           'description': self.clus1_desc,
                           'config': self.clus1_config}
        tmp = self.app.post('/clusters/',
                            content_type=self.content_type,
                            data=json.dumps(self.clus1_data))
        out = json.loads(tmp.data)
        self.clus1_id = out['cluster']['id']
        # neet to create a test role
        self.shep = 30

    @classmethod
    def tearDownClass(self):
        resp = self.app.delete('/clusters/%s' % self.clus1_id,
                               content_type=self.content_type)

    def _delete_node(self, node_id):
        # if self.foo.config['backend'] != 'null':
        #     time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/nodes/%s' % node_id,
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

    def test_create_node_with_hostname_only(self):
        data = {'hostname': self.hostname}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Node Created')
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['cluster_id'], None)
        self.assertEquals(out['node']['role'], None)
        self.assertEquals(out['node']['config'], dict())

        # Cleanup the node we created
        self._delete_node(out['node']['id'])

    def test_create_node_with_hostname_config_and_no_cluster_role(self):
        data = {'hostname': self.hostname,
                'config': self.attribs}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Node Created')
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['cluster_id'], None)
        self.assertEquals(out['node']['role'], None)
        self.assertEquals(out['node']['config'], self.attribs)

        # Cleanup the node we created
        self._delete_node(out['node']['id'])

    def test_create_node_with_hostname_config_cluster_and_no_role(self):
        data = {'hostname': self.hostname,
                'cluster_id': self.clus1_id,
                'config': self.attribs}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Node Created')
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['cluster_id'], self.clus1_id)
        self.assertEquals(out['node']['role'], None)
        self.assertEquals(out['node']['config'], self.attribs)

        # Cleanup the node we created
        self._delete_node(out['node']['id'])

    def test_create_node_with_hostname_config_cluster_role(self):
        data = {'hostname': self.hostname,
                'cluster_id': self.clus1_id,
                'role': 'test-role',
                'config': self.attribs}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        print(resp.status_code)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Node Created')
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['cluster_id'], self.clus1_id)
        self.assertEquals(out['node']['role'], 'test-role')
        self.assertEquals(out['node']['config'], self.attribs)

        # Cleanup the node we created
        self._delete_node(out['node']['id'])

    def test_create_node_without_hostname(self):
        data = {'description': self.desc,
                'config': self.attribs}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)

    def _generic_test(self, method, path, code):
        resp = self.app.__getattribute__(method)(
            path,
            content_type=self.content_type)
        self.assertEquals(resp.status_code, code)


class NodeUpdateTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()

    @classmethod
    def tearDownClass(self):
        pass

    def setUp(self):
        self.hostname = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {"package_component": "essex-final",
                        "monitoring": {"metric_provider": "null"}}
        self.role = None
        self.cluster_id = None
        self.backend = "unprovisioned"
        self.backend_state = "unknown"
        self.content_type = 'application/json'
        self.shep = 30
        self.create_data = {'hostname': self.hostname,
                            'config': self.attribs,
                            'role': self.role,
                            'cluster_id': self.cluster_id,
                            'backend': self.backend,
                            'backend_state': self.backend_state}
        tmp = self.app.post('/nodes/',
                            content_type=self.content_type,
                            data=json.dumps(self.create_data))
        self.json = json.loads(tmp.data)
        self.node_id = self.json['node']['id']
        # if self.foo.config['backend'] != 'null':
        #     time.sleep(2 * self.shep)  # chef-solr indexing can be slow

    def tearDown(self):
        tmp_resp = self.app.delete('/nodes/%s' + str(self.node_id),
                                   content_type=self.content_type)

    def test_update_node_attribute_config(self):
        tmp_desc = _randomStr(30)
        tmp_attribs = {'package_component': 'grizzly-final',
                       'monitoring': {'metric_provider': 'collectd'}}
        payload = {'config': tmp_attribs}
        resp = self.app.put('/nodes/%s/config' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['node']['id'], self.node_id)
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['role'], self.role)
        self.assertEquals(out['node']['cluster_id'], self.cluster_id)
        self.assertEquals(out['node']['backend'], self.backend)
        self.assertEquals(out['node']['backend_state'], self.backend_state)
        self.assertEquals(out['node']['config'], tmp_attribs)
        self.assertNotEquals(out['node']['config'], self.attribs)

    def test_update_node_attribute_id_returns_400(self):
        tmp_id = 99
        payload = {'id': tmp_id}
        resp = self.app.put('/nodes/%s/id' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)
        self.assertTrue('id is not modifiable' in out['message'])

    def test_update_node_attribute_hostname_returns_400(self):
        tmp_hostname = _randomStr(30)
        payload = {'hostname': tmp_hostname}
        resp = self.app.put('/nodes/%s/hostname' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)
        self.assertTrue('hostname is not modifiable' in out['message'])

    def test_update_node_attribute_role(self):
        # TODO(shep): Not sure if this should work with a non-existent
        #             role_id
        tmp_role = 'superfan99'
        payload = {'role': tmp_role}
        resp = self.app.put('/nodes/%s/role' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['node']['id'], self.node_id)
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['config'], self.attribs)
        self.assertEquals(out['node']['cluster_id'], self.cluster_id)
        self.assertEquals(out['node']['backend'], self.backend)
        self.assertEquals(out['node']['backend_state'], self.backend_state)
        self.assertEquals(out['node']['role'], tmp_role)
        self.assertNotEquals(out['node']['role'], self.role)

    def test_update_node_attribute_cluster_id(self):
        # TODO(shep): Not sure if this should work with a non-existent
        #             cluster_id
        tmp_cluster_id = 99
        payload = {'cluster_id': tmp_cluster_id}
        resp = self.app.put('/nodes/%s/cluster_id' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['node']['id'], self.node_id)
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['config'], self.attribs)
        self.assertEquals(out['node']['role'], self.role)
        self.assertEquals(out['node']['backend'], self.backend)
        self.assertEquals(out['node']['backend_state'], self.backend_state)
        self.assertEquals(out['node']['cluster_id'], tmp_cluster_id)
        self.assertNotEquals(out['node']['cluster_id'], self.cluster_id)

    def test_update_node_attribute_backend(self):
        tmp_backend = _randomStr(10)
        payload = {'backend': tmp_backend}
        resp = self.app.put('/nodes/%s/backend' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['node']['id'], self.node_id)
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['config'], self.attribs)
        self.assertEquals(out['node']['role'], self.role)
        self.assertEquals(out['node']['cluster_id'], self.cluster_id)
        self.assertEquals(out['node']['backend_state'], self.backend_state)
        self.assertEquals(out['node']['backend'], tmp_backend)
        self.assertNotEquals(out['node']['backend'], self.backend)

    def test_update_node_attribute_backend_state(self):
        tmp_backend_state = _randomStr(10)
        payload = {'backend_state': tmp_backend_state}
        resp = self.app.put('/nodes/%s/backend_state' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['node']['id'], self.node_id)
        self.assertEquals(out['node']['hostname'], self.hostname)
        self.assertEquals(out['node']['config'], self.attribs)
        self.assertEquals(out['node']['role'], self.role)
        self.assertEquals(out['node']['cluster_id'], self.cluster_id)
        self.assertEquals(out['node']['backend'], self.backend)
        self.assertEquals(out['node']['backend_state'], tmp_backend_state)
        self.assertNotEquals(out['node']['backend_state'], self.backend_state)

    def test_update_node_attribute_config_with_bad_data_returns_400(self):
        payload = {'backend': _randomStr(10)}
        resp = self.app.put('/nodes/%s/config' % self.node_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)
        self.assertTrue('Empty body' in out['message'])

    def test_update_node_with_no_data(self):
        resp = self.app.put('/nodes/%s' % self.node_id,
                            data=None,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 400)


class NodeInvalidHTTPMethodTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.content_type = 'application/json'

    @classmethod
    def tearDownClass(self):
        pass

    def _execute_method(self, method_name, path, http_code):
        """Helper function that will execute a method, against a path and
           verify the returned http code

        :param method_name: name of the http method to execute
        :param path: path to execute the http call against
        :param http_code: http error code to validate against
        """
        resp = self.app.__getattribute__(method_name)(
            path,
            content_type=self.content_type)
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
