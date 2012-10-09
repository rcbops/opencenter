# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import roush
import string
import unittest2
import tempfile
import time

from test_roush import RoushTestCase
from setup import RoushTest

from db.database import init_db
import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class ClusterCreateTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
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

    @classmethod
    def tearDownClass(self):
        pass

    def _delete_cluster(self, cluster_id):
        resp = self.app.delete('/clusters/%s' % cluster_id,
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Cluster deleted')

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
        self._delete_cluster(out['cluster']['id'])

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
        self.assertEquals(out['cluster']['config'], dict())

        # Cleanup the cluster we created
        self._delete_cluster(out['cluster']['id'])

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
        self._delete_cluster(out['cluster']['id'])

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
        self.assertEquals(out['cluster']['config'], dict())

        # Cleanup the cluster we created
        self._delete_cluster(out['cluster']['id'])

    def test_create_cluster_without_name_TODO(self):
        # TODO(shep): currently this passes, but a cluster should
        #             not be able to be created with out a name

        #data = {'description': self.desc,
        #        'config': self.attribs}
        #resp = self.app.post('/clusters/',
        #                     content_type=self.content_type,
        #                     data=json.dumps(data))
        #self.assertEquals(resp.status_code, 400)
        #out = json.loads(resp.data)
        #self.assertEquals(out['status'], 400)
        pass

    def test_create_duplicate_cluster_returns_a_400_TODO(self):
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

        # Lets create a duplicate entry
        data = {'name': self.name,
                'description': self.desc,
                'config': self.attribs}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        tmp = json.loads(resp.data)
        self.assertEquals(tmp['status'], 400)
        # Error messages suck right now.. need to make them better
        # self.assertTrue('foo' in tmp['message'])

        # Cleanup the cluster we created
        self._delete_cluster(out['cluster']['id'])


class ClusterUpdateTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        self.app = self.foo.test_client()
        self.content_type = 'application/json'

    @classmethod
    def tearDownClass(self):
        pass

    def setUp(self):
        self.name = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {"package_component": "essex-final",
                        "monitoring": {"metric_provider": "null"}}
        self.data = {'name': self.name,
                     'description': self.desc,
                     'config': self.attribs}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(self.data))
        out = json.loads(resp.data)
        self.cluster_id = out['cluster']['id']

    def tearDown(self):
        resp = self.app.delete('/clusters/%s' % self.cluster_id,
                               content_type=self.content_type)

    def test_update_cluster_attribute_name_returns_a_400_TODO(self):
        # TODO(shep): currently this passes, but an update
        #             against the name attribute should fail

        tmp_name = _randomStr(10)
        payload = {'name': tmp_name}
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEqual(out['status'], 400)
        self.assertTrue('Attribute name is not modifiable' in out['message'])
        # pass

    def test_update_cluster_attribute_name_by_uri_returns_a_400(self):
        tmp_name = _randomStr(10)
        payload = {'name': tmp_name}
        resp = self.app.put('/clusters/%s/name' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEqual(out['status'], 400)
        self.assertTrue('Attribute name is not modifiable' in out['message'])

    def test_update_cluster_attribute_description(self):
        tmp_desc = _randomStr(30)
        payload = {'description': tmp_desc}
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], tmp_desc)
        self.assertNotEquals(out['cluster']['description'], self.desc)

    def test_update_cluster_attribute_description_by_uri(self):
        tmp_desc = _randomStr(30)
        payload = {'description': tmp_desc}
        resp = self.app.put('/clusters/%s/description' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], tmp_desc)
        self.assertNotEquals(out['cluster']['description'], self.desc)

    def test_update_cluster_attribute_description_by_uri_bad_data_400(self):
        tmp_desc = _randomStr(30)
        payload = {'foo': tmp_desc}
        resp = self.app.put('/clusters/%s/description' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)
        self.assertEquals(out['message'], 'Empty body')

    def test_update_cluster_attribute_config(self):
        tmp_attribs = {'package_component': 'grizzly-final',
                       'monitoring': {'metric_provider': 'collectd'}}
        data = {'config': tmp_attribs}
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(data))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], self.desc)
        self.assertEquals(out['cluster']['config'],
                          tmp_attribs)
        self.assertNotEquals(out['cluster']['config'],
                             self.attribs)

    def test_update_cluster_attribute_config_by_uri(self):
        tmp_attribs = {'package_component': 'grizzly-final',
                       'monitoring': {'metric_provider': 'collectd'}}
        data = {'config': tmp_attribs}
        resp = self.app.put('/clusters/%s/config' % self.cluster_id,
                            content_type=self.content_type,
                            data=json.dumps(data))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], self.desc)
        self.assertEquals(out['cluster']['config'],
                          tmp_attribs)
        self.assertNotEquals(out['cluster']['config'],
                             self.attribs)

    def test_patch_on_cluster_attribute_config(self):
        tmp_attribs = {'monitoring': {'metric_provider': 'collectd'}}
        resp = self.app.patch('/clusters/%s/config' % self.cluster_id,
                              data=json.dumps(tmp_attribs),
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['cluster']['config']['monitoring'],
                          tmp_attribs['monitoring'])
        self.assertNotEquals(out['cluster']['config']['monitoring'],
                             self.attribs['monitoring'])

    def test_patch_on_cluster_attribute_config_bad_cluster_404(self):
        tmp_attribs = {'monitoring': {'metric_provider': 'collectd'}}
        resp = self.app.patch('/clusters/%s/config' % '99',
                            data=json.dumps(tmp_attribs),
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 404)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 404)
        self.assertTrue('Not Found' in out['message'])

    def test_update_cluster_with_no_data(self):
        resp = self.app.put('/clusters/%s' % self.cluster_id,
                            data=None,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 400)


class ClusterReadTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        self.app = self.foo.test_client()
        self.content_type = 'application/json'
        self.name = _randomStr(10)
        self.desc = _randomStr(30)
        self.data = {'name': self.name,
                     'description': self.desc}
        resp = self.app.post('/clusters/',
                             content_type=self.content_type,
                             data=json.dumps(self.data))
        out = json.loads(resp.data)
        self.cluster_id = out['cluster']['id']

    @classmethod
    def tearDownClass(self):
        resp = self.app.delete('/clusters/%s' % self.cluster_id,
                               content_type=self.content_type)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_read_cluster_list(self):
        resp = self.app.get('/clusters/', content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(len(out['clusters']), 1)
        self.assertEquals(out['clusters'][0]['name'], self.name)
        self.assertEquals(out['clusters'][0]['description'], self.desc)

    def test_read_cluster_by_id(self):
        resp = self.app.get('/clusters/%s' % self.cluster_id,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['cluster']['name'], self.name)
        self.assertEquals(out['cluster']['description'], self.desc)

    def test_read_cluster_attribute_name_by_uri_with_bad_id_404(self):
        resp = self.app.get('/clusters/%s/name' % '99',
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 404)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 404)
        self.assertTrue('Not Found' in out['message'])

    def test_read_cluster_attribute_name_by_uri(self):
        resp = self.app.get('/clusters/%s/name' % self.cluster_id,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['name'], self.name)

    def test_read_cluster_attribute_description_by_uri(self):
        resp = self.app.get('/clusters/%s/description' % self.cluster_id,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['description'], self.desc)


class ClusterUpdateAttributeTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
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
        self.assertEquals(out['nodes'], list())

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
        self.assertEquals(out['node']['config'], dict())

        # make sure /clusters/<cluster_id>/nodes looks right
        resp = self.app.get('/clusters/%s/nodes' % self.cluster_id,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEquals(len(tmp['nodes']), 1)
        self.assertEquals(tmp['nodes'][0]['id'], out['node']['id'])
        self.assertEquals(tmp['nodes'][0]['hostname'], hostname)

        # Cleanup the node we created
        resp = self.app.delete('/nodes/%s' % out['node']['id'],
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

    def tearDown(self):
        tmp_resp = self.app.delete('/clusters/%s' % self.cluster_id,
                                   content_type=self.content_type)


class ClusterInvalidHTTPMethodTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.content_type = 'application/json'

    def test_405_returned_by_patch_on_cluster_attribute_id(self):
        resp = self.app.patch('/clusters/1/id',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_405_returned_by_patch_on_cluster_attribute_name(self):
        resp = self.app.patch('/clusters/1/name',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_405_returned_by_patch_on_cluster_attribute_description(self):
        resp = self.app.patch('/clusters/1/description',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_405_returned_by_delete_on_clusters(self):
        resp = self.app.delete('/clusters/',
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_405_returned_by_patch_on_clusters(self):
        resp = self.app.patch('/clusters/',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_405_returned_by_put_on_clusters(self):
        resp = self.app.put('/clusters/',
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_405_returned_by_post_on_clusters_with_id(self):
        resp = self.app.post('/clusters/1',
                             content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)

    def test_405_returned_by_patch_on_clusters_with_id(self):
        resp = self.app.patch('/clusters/1',
                              content_type=self.content_type)
        self.assertEquals(resp.status_code, 405)
