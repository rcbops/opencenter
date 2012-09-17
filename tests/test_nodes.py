# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import roush
import string
import unittest
import tempfile
import time

from test_roush import RoushTestCase
from setup import RoushTest

from db.database import init_db
import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class NodeCreateTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='local.conf', debug=True)
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
        self.assertEquals(out['node']['role_id'], None)
        self.assertEquals(out['node']['config'], None)

        # Cleanup the node we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/nodes/%s' % out['node']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

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
        self.assertEquals(out['node']['role_id'], None)
        self.assertEquals(out['node']['config'], self.attribs)

        # Cleanup the node we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/nodes/%s' % out['node']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

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
        self.assertEquals(out['node']['role_id'], None)
        self.assertEquals(out['node']['config'], self.attribs)

        # Cleanup the node we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/nodes/%s' % out['node']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

    def test_create_node_with_hostname_config_cluster_role(self):
        data = {'hostname': self.hostname,
                'cluster_id': self.clus1_id,
                'role_id': 2,
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
        self.assertEquals(out['node']['role_id'], 2)
        self.assertEquals(out['node']['config'], self.attribs)

        # Cleanup the node we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/nodes/%s' % out['node']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')
        # self.assertTrue(False)

    def test_create_node_without_hostname(self):
        data = {'description': self.desc,
                'config': self.attribs}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)

    def test_verify_delete_method_returns_a_405_on_nodes(self):
        resp = self.app.delete('/nodes/',
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_verify_patch_method_returns_a_405_on_nodes(self):
        resp = self.app.patch('/nodes/',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_verify_put_method_returns_a_405_on_nodes(self):
        resp = self.app.put('/nodes/',
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)


class NodeUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='local.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()

    def setUp(self):
#        self.hostname = _randomStr(10)
#        self.desc = _randomStr(30)
#        self.attribs = {"package_component": "essex-final",
#                        "monitoring": {"metric_provider": "null"}}
        self.content_type = 'application/json'
#        self.shep = 30
#        self.create_data = {'hostname': self.hostname,
#                            'description': self.desc,
#                            'config': self.attribs}
#        tmp = self.app.post('/nodes/',
#                            content_type=self.content_type,
#                            data=json.dumps(self.create_data))
#        self.json = json.loads(tmp.data)
#        self.node_id = self.json['node']['id']
#        if self.foo.config['backend'] != 'null':
#            time.sleep(2 * self.shep)  # chef-solr indexing can be slow

#    def test_update_node_with_description_and_override_attributes(self):
#        tmp_desc = _randomStr(30)
#        tmp_attribs = {'package_component': 'grizzly-final',
#                       'monitoring': {'metric_provider': 'collectd'}}
#        data = {'hostname': self.hostname,
#                'description': tmp_desc,
#                'config': tmp_attribs}
#        resp = self.app.put('/nodes/%s' % self.node_id,
#                            content_type=self.content_type,
#                            data=json.dumps(data))
#        self.assertEquals(resp.status_code, 200)
#        out = json.loads(resp.data)
#        self.assertEquals(out['id'], self.node_id)
#        self.assertEquals(out['hostname'], self.hostname)
#        self.assertEquals(out['description'], tmp_desc)
#        self.assertNotEquals(out['description'], self.desc)
#        self.assertEquals(out['config'], tmp_attribs)
#        self.assertNotEquals(out['config'], self.attribs)

#    def test_update_node_with_description_and_no_override_attributes(self):
#        tmp_desc = _randomStr(30)
#        data = {'hostname': self.hostname,
#                'description': tmp_desc}
#        resp = self.app.put('/nodes/%s' % self.node_id,
#                            content_type=self.content_type,
#                            data=json.dumps(data))
#        self.assertEquals(resp.status_code, 200)
#        out = json.loads(resp.data)
#        self.assertEquals(out['id'], self.node_id)
#        self.assertEquals(out['hostname'], self.hostname)
#        self.assertEquals(out['description'], tmp_desc)
#        self.assertNotEquals(out['description'], self.desc)
#        self.assertEquals(out['config'], self.attribs)

#    def test_update_node_with_override_attributes_and_no_description(self):
#        tmp_attribs = {'package_component': 'grizzly-final',
#                       'monitoring': {'metric_provider': 'collectd'}}
#        data = {'hostname': self.hostname,
#                'config': tmp_attribs}
#        resp = self.app.put('/nodes/%s' % self.node_id,
#                            content_type=self.content_type,
#                            data=json.dumps(data))
#        self.assertEquals(resp.status_code, 200)
#        out = json.loads(resp.data)
#        self.assertEquals(out['id'], self.node_id)
#        self.assertEquals(out['hostname'], self.hostname)
#        self.assertEquals(out['description'], self.desc)
#        self.assertEquals(out['config'], tmp_attribs)
#        self.assertNotEquals(out['config'], self.attribs)

#    def test_update_node_with_no_data(self):
#        resp = self.app.put('/nodes/%s' % self.node_id,
#                            data=None,
#                            content_type=self.content_type)
#        self.assertEquals(resp.status_code, 400)

    def test_verify_post_method_returns_a_405_on_nodes_with_id(self):
        resp = self.app.post('/nodes/1',
                             content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_verify_patch_method_returns_a_405_on_nodes_with_id(self):
        resp = self.app.patch('/nodes/1',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

#    def tearDown(self):
#        tmp_resp = self.app.delete('/nodes/%s' + str(self.node_id),
#                                   content_type=self.content_type)
