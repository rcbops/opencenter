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


class RoleCRUDTestCase(unittest.TestCase):

    def setUp(self):
        # This has to be set to expose tracebacks
        # roush.app.testing = True
        # self.app = roush.app.test_client()
        foo = webapp.Thing(configfile='local.conf', debug = True)
        self.app = foo.test_client()


    def tearDown(self):
        pass

    def test_role_crud(self):
        tmp_name = _randomStr(10)
        tmp_description = "lorem ipsum"

        # create a new role
        role = {"name": tmp_name, "description": tmp_description}
        resp = self.app.post('/roles', data=json.dumps(role), content_type='application/json')
        # pprint(resp)
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)

        # make sure the role was created
        resp = self.app.get('/roles/%s' % data['role']['id'])
        tmp = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(tmp['id'], data['role']['id'])
        self.assertEqual(tmp['name'], tmp_name)
        self.assertEqual(tmp['description'], tmp_description)

        # update role attributes
        new_desc = "updated description"
        new_role = {"description": new_desc}
        resp = self.app.put('/roles/%s' % data['role']['id'], data=json.dumps(new_role), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        tmp_data = json.loads(resp.data)
        self.assertEqual(tmp_data['description'], new_desc)

        # clean up the role
        resp = self.app.delete('/roles/%s' % data['role']['id'])
        self.assertEqual(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEqual(tmp['status'], 200)
        self.assertEqual(tmp['message'], 'Role deleted')


class RoleTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # This has to be set to expose tracebacks
        foo = webapp.Thing(configfile='local.conf', debug = True)
        self.app = foo.test_client()
        # roush.app.testing = True
        # self.app = roush.app.test_client()
        # Create a role
        self.role_name = _randomStr(10)
        self.role_desc = _randomStr(30)
        self.role_data = {"name": self.role_name, "description": self.role_desc}
        tmp = self.app.post('/roles', data=json.dumps(self.role_data), content_type='application/json')
        self.role_json = json.loads(tmp.data)
        self.role_id = self.role_json['role']['id']

    @classmethod
    def tearDownClass(self):
        tmp = self.app.delete('/roles/%s' % self.role_id)

    def test_role_blah(self):
        pass

if __name__ == '__main__':
    unittest.main()
