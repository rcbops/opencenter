# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
from pprint import pprint
import random
import string
import unittest2
import tempfile

import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class RoleCreateTests(unittest2.TestCase):
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

    def tearDown(self):
        pass

    def _delete_role(self, role_id):
        resp = self.app.delete("/roles/%d" % role_id,
                               content_type=self.content_type)
        self.assertEqual(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEqual(tmp['status'], 200)
        self.assertEqual(tmp['message'], 'Role deleted')

    def test_create_role(self):
        data = {'name': self.name,
                'description': self.desc}
        resp = self.app.post('/roles/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEqual(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Role Created')
        self.assertEquals(out['role']['name'], self.name)
        self.assertEquals(out['role']['description'], self.desc)

        # clean up the role we created
        self._delete_role(out['role']['id'])


class RoleUpdateTests(unittest2.TestCase):
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
        self.data = {'name': self.name,
                     'description': self.desc}
        resp = self.app.post('/roles/',
                             content_type=self.content_type,
                             data=json.dumps(self.data))
        out = json.loads(resp.data)
        self.role_id = out['role']['id']

    def tearDown(self):
        resp = self.app.delete('/roles/%s' % self.role_id,
                               content_type=self.content_type)

    def test_update_role_attribute_name(self):
        tmp_name = _randomStr(10)
        payload = {'name': tmp_name}
        resp = self.app.put('/roles/%s' % self.role_id,
                             content_type=self.content_type,
                             data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['role']['name'], tmp_name)
        self.assertNotEquals(out['role']['name'], self.name)
        self.assertEquals(out['role']['description'], self.desc)

    def test_update_role_attribute_name_by_uri(self):
        tmp_name = _randomStr(10)
        payload = {'name': tmp_name}
        resp = self.app.put('/roles/%s/name' % self.role_id,
                             content_type=self.content_type,
                             data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['role']['name'], tmp_name)
        self.assertNotEquals(out['role']['name'], self.name)
        self.assertEquals(out['role']['description'], self.desc)

    def test_update_role_attribute_description(self):
        tmp_desc = _randomStr(30)
        payload = {'description': tmp_desc}
        resp = self.app.put('/roles/%s' % self.role_id,
                             content_type=self.content_type,
                             data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['role']['name'], self.name)
        self.assertEquals(out['role']['description'], tmp_desc)
        self.assertNotEquals(out['role']['description'], self.desc)

    def test_update_role_attribute_description_by_uri(self):
        tmp_desc = _randomStr(30)
        payload = {'description': tmp_desc}
        resp = self.app.put('/roles/%s/description' % self.role_id,
                             content_type=self.content_type,
                             data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['role']['name'], self.name)
        self.assertEquals(out['role']['description'], tmp_desc)
        self.assertNotEquals(out['role']['description'], self.desc)


class RoleInvalidHTTPMethodTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
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

    def test_405_returned_by_delete_on_roles(self):
        self._execute_method('delete', '/roles/', 405)

    def test_405_returned_by_patch_on_roles(self):
        self._execute_method('patch', '/roles/', 405)

    def test_405_returned_by_put_on_roles(self):
        self._execute_method('put', '/roles/', 405)

    def test_405_returned_by_post_on_roles_with_id(self):
        self._execute_method('post', '/roles/99', 405)

    def test_405_returned_by_patch_on_roles_with_id(self):
        self._execute_method('patch', '/roles/99', 405)
