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


class ClusterCreateTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='local.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.app.testing = True
        self.name = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {_randomStr(5): _randomStr(10),
                        _randomStr(5): {_randomStr(5): _randomStr(10)},
                        _randomStr(5): [_randomStr(10), _randomStr(10)]}
        self.content_type = 'application/json'
        self.shep = 30

    def test_create_cluster_with_desc_and_override_attributes(self):
        data = {'name': self.name,
                'description': self.desc,
                'config': self.attribs}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Cluster Created')
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], self.desc)
        self.assertEquals(out['cluster']['config'], self.attribs)

        # Cleanup the cluster we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/clusters/%s' % out['cluster']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Cluster deleted')

    def test_create_cluster_with_desc_and_no_override_attributes(self):
        data = {'name': self.name,
                'description': self.desc}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Cluster Created')
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], self.desc)
        self.assertEquals(out['cluster']['config'], None)

        # Cleanup the cluster we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/clusters/%s' % out['cluster']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Cluster deleted')

    def test_create_cluster_with_override_attributes_and_no_desc(self):
        data = {'name': self.name,
                'config': self.attribs}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Cluster Created')
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], None)
        self.assertEquals(out['cluster']['config'], self.attribs)

        # Cleanup the cluster we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/clusters/%s' % out['cluster']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Cluster deleted')

    def test_create_cluster_with_no_desc_and_no_override_attributes(self):
        data = {'name': self.name}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Cluster Created')
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], None)
        self.assertEquals(out['cluster']['config'], None)

        # Cleanup the cluster we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/clusters/%s' % out['cluster']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Cluster deleted')

    def test_create_cluster_without_name(self):
        data = {'description': self.desc,
                'config': self.attribs}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)

    def test_verify_delete_method_returns_a_405_on_clusters(self):
        resp = self.app.delete('/clusters/',
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_verify_patch_method_returns_a_405_on_clusters(self):
        resp = self.app.patch('/clusters/',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_verify_put_method_returns_a_405_on_clusters(self):
        resp = self.app.put('/clusters/',
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)


class ClusterUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='local.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()

    def setUp(self):
        self.name = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {"package_component": "essex-final",
                        "monitoring": {"metric_provider": "null"}}
        self.content_type = 'application/json'
        self.shep = 30
        self.create_data = {'name': self.name,
                            'description': self.desc,
                            'config': self.attribs}
        tmp = self.app.post('/clusters/',
                            content_type=self.content_type,
                            data=json.dumps(self.create_data))
        self.json = json.loads(tmp.data)
        self.cluster_id = self.json['cluster']['id']
        if self.foo.config['backend'] != 'null':
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow

    def test_update_cluster_with_description_and_override_attributes(self):
        tmp_desc = _randomStr(30)
        tmp_attribs = {'package_component': 'grizzly-final',
                       'monitoring': {'metric_provider': 'collectd'}}
        data = {'name': self.name,
                'description': tmp_desc,
                'config': tmp_attribs}
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(data))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['id'], self.cluster_id)
        self.assertEquals(out['name'], self.name)
        self.assertEquals(out['description'], tmp_desc)
        self.assertNotEquals(out['description'], self.desc)
        self.assertEquals(out['config'], tmp_attribs)
        self.assertNotEquals(out['config'], self.attribs)

    def test_update_cluster_with_description_and_no_override_attributes(self):
        tmp_desc = _randomStr(30)
        data = {'name': self.name,
                'description': tmp_desc}
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(data))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['id'], self.cluster_id)
        self.assertEquals(out['name'], self.name)
        self.assertEquals(out['description'], tmp_desc)
        self.assertNotEquals(out['description'], self.desc)
        self.assertEquals(out['config'], self.attribs)

    def test_update_cluster_with_override_attributes_and_no_description(self):
        tmp_attribs = {'package_component': 'grizzly-final',
                       'monitoring': {'metric_provider': 'collectd'}}
        data = {'name': self.name,
                'config': tmp_attribs}
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(data))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['id'], self.cluster_id)
        self.assertEquals(out['name'], self.name)
        self.assertEquals(out['description'], self.desc)
        self.assertEquals(out['config'], tmp_attribs)
        self.assertNotEquals(out['config'], self.attribs)

    def test_update_cluster_with_no_data(self):
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            data=None,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 400)

    def test_verify_post_method_returns_a_405_on_clusters_with_id(self):
        resp = self.app.post('/clusters/%s' % self.cluster_id,
                             content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    # TODO(shep): this method probably should not be part of the
    #             allowed method list.
    def test_verify_patch_method_returns_a_501_on_clusters_with_id(self):
        resp = self.app.patch('/clusters/%s' % self.cluster_id,
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 501)

    def tearDown(self):
        tmp_resp = self.app.delete('/clusters/%s' % self.cluster_id,
                                   content_type=self.content_type)


class ClusterAttributeTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='local.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()

    def setUp(self):
        self.name = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {"package_component": "essex-final",
                        "monitoring": {"metric_provider": "null"}}
        self.content_type = 'application/json'
        self.shep = 30
        self.create_data = {'name': self.name,
                            'description': self.desc,
                            'config': self.attribs}
        tmp = self.app.post('/clusters/',
                            content_type=self.content_type,
                            data=json.dumps(self.create_data))
        self.json = json.loads(tmp.data)
        self.cluster_id = self.json['cluster']['id']
        if self.foo.config['backend'] != 'null':
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow

    def test_cluster_node_list_on_non_existent_cluster_id(self):
        resp = self.app.get('/clusters/99/nodes',
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 404)

    def test_cluster_node_list_on_cluster_id_with_empty_nodes_list(self):
        resp = self.app.get('/clusters/1/nodes',
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(len(out['nodes']), 0)

    def test_cluster_node_list(self):
        # Create a node with cluster_id=self.cluster_id
        hostname = _randomStr(10)
        data = {'hostname': hostname,
                'cluster_id': self.cluster_id}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Node Created')
        self.assertEquals(out['node']['hostname'], hostname)
        self.assertEquals(out['node']['cluster_id'], self.cluster_id)
        self.assertEquals(out['node']['role_id'], None)
        self.assertEquals(out['node']['config'], None)

        # make sure /clusters/<cluster_id>/nodes looks right
        resp = self.app.get('/clusters/%s/nodes' % self.cluster_id,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEquals(len(tmp['nodes']), 1)
        self.assertEquals(tmp['nodes'][0]['id'], 1)
        self.assertEquals(tmp['nodes'][0]['hostname'], hostname)

        # Cleanup the node we created
        if self.foo.config['backend'] != "null":
            time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/nodes/%s' % out['node']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

    def tearDown(self):
        tmp_resp = self.app.delete('/clusters/%s' % self.cluster_id,
                                   content_type=self.content_type)
