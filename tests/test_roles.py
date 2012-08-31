# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
from pprint import pprint
import random
import string
import unittest
import tempfile

import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class RoleCRUDTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        foo = webapp.Thing("roush", configfile='local.conf', debug=True)
        self.app = foo.test_client()

        self.role_name = _randomStr(10)
        self.role_desc = _randomStr(30)
        self.content_type = 'application/json'

    def test_role_crud(self):
        # create a new role
        role = {'name': self.role_name,
                'description': self.role_desc}
        resp = self.app.post('/roles/', data=json.dumps(role),
                             content_type=self.content_type)
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)

        # make sure the role was created
        resp = self.app.get("/roles/%s" % data['role']['id'],
                            content_type=self.content_type)

        tmp = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(tmp['id'], data['role']['id'])
        self.assertEqual(tmp['name'], self.role_name)
        self.assertEqual(tmp['description'], self.role_desc)

        # update role attributes
        new_desc = _randomStr(30)
        new_role = {"description": new_desc}
        resp = self.app.put("/roles/%d" % data['role']['id'],
                            data=json.dumps(new_role),
                            content_type=self.content_type)
        self.assertEqual(resp.status_code, 200)
        tmp_data = json.loads(resp.data)
        self.assertEqual(tmp_data['description'], new_desc)
        self.assertNotEqual(tmp_data['description'], self.role_desc)

        # clean up the role
        resp = self.app.delete("/roles/%d" % data['role']['id'],
                               content_type=self.content_type)
        self.assertEqual(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEqual(tmp['status'], 200)
        self.assertEqual(tmp['message'], 'Role deleted')


#class RoleTestCase(RoushTestCase):

#    @classmethod
#    def setUpClass(self):
        # roush.app.testing = True
        # self.app = roush.app.test_client()
        # Create a role
    #     self.role_name = _randomStr(10)
    #     self.role_desc = _randomStr(30)
    #     self.role_data = {
    #         "name": self.role_name,
    #         "description": self.role_desc}
    #     tmp = self.app.post('/roles', data=json.dumps(self.role_data),
    #                         content_type='application/json')
    #     self.role_json = json.loads(tmp.data)
    #     self.role_id = self.role_json['role']['id']

    # @classmethod
    # def tearDownClass(self):
    #     tmp = self.app.delete('/roles/%s' % self.role_id)

    # def test_role_blah(self):
    #     pass

if __name__ == '__main__':
    unittest.main()
