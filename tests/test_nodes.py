# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import roush
import string
import unittest
import tempfile

import webapp

def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class NodeCRUDTestCase(unittest.TestCase):

    def setUp(self):
        # This has to be set to expose tracebacks
        foo = webapp.Thing(configfile='local.conf', debug = True)
        self.app = foo.test_client()

        # roush.app.testing = True
        # self.app = roush.app.test_client()

    def tearDown(self):
        pass

    def test_node_crud(self):
        tmp_name = _randomStr(10)
        tmp_description = "lorem ipsum"

        # create a new node
        node = {"name": tmp_name, "description": tmp_description}
        resp = self.app.post('/nodes', data=json.dumps(node), content_type='application/json')
        # pprint(resp)
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)

        # make sure the node was created
        resp = self.app.get('/nodes/%s' % data['node']['id'])
        tmp = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(tmp['id'], data['node']['id'])
        self.assertEqual(tmp['name'], tmp_name)
        self.assertEqual(tmp['description'], tmp_description)

        # update node attributes
        new_desc = "updated description"
        new_node = {"description": new_desc}
        resp = self.app.put('/nodes/%s' % data['node']['id'], data=json.dumps(new_node), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        tmp_data = json.loads(resp.data)
        self.assertEqual(tmp_data['description'], new_desc)

        # clean up the node
        resp = self.app.delete('/nodes/%s' % data['node']['id'])
        self.assertEqual(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEqual(tmp['status'], 200)
        self.assertEqual(tmp['message'], 'Role deleted')


class NodeTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # This has to be set to expose tracebacks
        foo = webapp.Thing(configfile='local.conf', debug = True)
        self.app = foo.test_client()
        # roush.app.testing = True
        # self.app = roush.app.test_client()
        # Create a node
        self.node_name = _randomStr(10)
        self.node_desc = _randomStr(30)
        self.node_data = {"name": self.node_name, "description": self.node_desc}
        tmp = self.app.post('/nodes', data=json.dumps(self.node_data), content_type='application/json')
        self.node_json = json.loads(tmp.data)
        self.node_id = self.node_json['node']['id']

    @classmethod
    def tearDownClass(self):
        tmp = self.app.delete('/nodes/%s' % self.node_id)

    def test_node_blah(self):
        pass

if __name__ == '__main__':
    unittest.main()
