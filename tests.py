#!/usr/bin/env python
import json
import os
import random
import roush
import string
import unittest
import tempfile

import database

class RoushTestCase(unittest.TestCase):

    def setUp(self):
        self.app = roush.app.test_client()

    def tearDown(self):
        pass

    def _generateRandomString(self,size):
        return "".join(random.choice(string.ascii_lowercase) for x in range(size))

    def test_empty_nodes(self):
        resp = self.app.get('/nodes')
        v = json.loads(resp.data)
        self.assertEqual(v['nodes'], [])

    def test_empty_clusters(self):
        resp = self.app.get('/clusters')
        v = json.loads(resp.data)
        self.assertEqual(v['clusters'], [])

    def test_empty_roles(self):
        resp = self.app.get('/roles')
        v = json.loads(resp.data)
        self.assertEqual(v['roles'], [])

    def test_create_role(self):
        name = self._generateRandomString(10)
        print name
        role_data = {"name": name, "description": "some text"}
        print json.dumps(role_data)
        resp = self.app.post('/roles', json.dumps(role_data))
        print resp

if __name__ == '__main__':
    unittest.main()
