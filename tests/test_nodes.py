# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import roush
import string
import unittest
import tempfile


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class NodeCRUDTestCase(unittest.TestCase):

    def setUp(self):
        # This has to be set to expose tracebacks
        roush.app.testing = True
        self.app = roush.app.test_client()
        self.content_type = 'application/json'

    def tearDown(self):
        pass

    def test_node_crud(self):
        tmp_name = _randomStr(10)
        tmp_description = "lorem ipsum"

        # create a new node
        node = {"name": tmp_name, "description": tmp_description}
        tmp_data = json.dumps(node)
        resp = self.app.post('/nodes', data=tmp_data, content_type=self.content_type)
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        url = '/nodes/%s' % data['node']['id']

        # make sure the node was created
        resp = self.app.get(url)
        tmp = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(tmp['id'], data['node']['id'])
        self.assertEqual(tmp['name'], tmp_name)
        self.assertEqual(tmp['description'], tmp_description)

        # update node attributes
        new_desc = "updated description"
        new_node = {"description": new_desc}
        resp = self.app.put(url, data=json.dumps(new_node), content_type=self.content_type)
        self.assertEqual(resp.status_code, 200)
        tmp_data = json.loads(resp.data)
        self.assertEqual(tmp_data['description'], new_desc)

        # clean up the node
        resp = self.app.delete(url)
        self.assertEqual(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEqual(tmp['status'], 200)
        self.assertEqual(tmp['message'], 'Role deleted')


class NodeTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # This has to be set to expose tracebacks
        roush.app.testing = True
        self.app = roush.app.test_client()
        self.content_type = 'application/json'
        self.list_url = '/nodes'
        # Create a node
        self.node_hostname = "%s.%s.%s" % (_randomStr(10), _randomStr(10), _randomStr(10))
        self.node_desc = _randomStr(30)
        self.node_data = {"hostname": self.node_hostname, "description": self.node_desc}
        tmp = self.app.post(self.list_url, data=json.dumps(self.node_data), content_type=self.content_type)
        self.node_json = json.loads(tmp.data)
        self.node_id = self.node_json['node']['id']
        self.node_url = '/nodes/%s' % self.node_id

    @classmethod
    def tearDownClass(self):
        tmp = self.app.delete(self.node_url)

    def test_node_blah(self):
        pass

if __name__ == '__main__':
    unittest.main()
