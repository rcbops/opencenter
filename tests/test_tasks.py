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
# from setup import RoushTest

from db.database import init_db
import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class TaskCreateTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.content_type = 'application/json'

    @classmethod
    def tearDownClass(self):
        pass

    def setUp(self):
        self.node_id = 99
        self.action = _randomStr(10)
        self.payload = {_randomStr(5): _randomStr(10),
                        _randomStr(5): {_randomStr(5): _randomStr(10)},
                        _randomStr(5): [_randomStr(10), _randomStr(10)]}
        self.state = 'pending'
        self.result = {_randomStr(5): _randomStr(10),
                       _randomStr(5): {_randomStr(5): _randomStr(10)},
                       _randomStr(5): [_randomStr(10), _randomStr(10)]}

    def tearDown(self):
        pass

    # NOTE(shep): tasks are not deletable
    def _delete_task(self, task_id):
        resp = self.app.delete('/tasks/%s' % task_id,
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Task deleted')

    def test_create_task_with_required_fields_only(self):
        # required fields: node_id, action, payload, state
        # optional fields: result, submitted, completed, expires
        data = {'node_id': self.node_id,
                'action': self.action,
                'payload': self.payload,
                'state': self.state,
                'result': self.result}
        resp = self.app.post('/tasks/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 201)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Task Created')
        self.assertEquals(out['task']['node_id'], self.node_id)
        self.assertEquals(out['task']['action'], self.action)
        self.assertEquals(out['task']['payload'], self.payload)
        self.assertEquals(out['task']['state'], self.state)
        self.assertEquals(out['task']['result'], self.result)

        # Clean up the task we created
        # NOTE(shep): tasks are not deletable
        self._delete_task(out['task']['id'])


class TaskUpdateTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.content_type = 'application/json'

    @classmethod
    def tearDownClass(self):
        pass

    def setUp(self):
        # required fields: node_id, action, payload, state
        # optional fields: result, submitted, completed, expires
        self.node_id = 99
        self.action = _randomStr(10)
        self.payload = {_randomStr(5): _randomStr(10),
                        _randomStr(5): {_randomStr(5): _randomStr(10)},
                        _randomStr(5): [_randomStr(10), _randomStr(10)]}
        self.state = 'pending'
        self.result = {_randomStr(5): _randomStr(10),
                       _randomStr(5): {_randomStr(5): _randomStr(10)},
                       _randomStr(5): [_randomStr(10), _randomStr(10)]}
        self.data = {'node_id': self.node_id,
                     'action': self.action,
                     'payload': self.payload,
                     'state': self.state,
                     'result': self.result}
        tmp = self.app.post('/tasks/',
                            content_type=self.content_type,
                            data=json.dumps(self.data))
        out = json.loads(tmp.data)
        self.task_id = out['task']['id']

    def tearDown(self):
        resp = self.app.delete('/tasks/%s' % self.task_id,
                               content_type=self.content_type)

    def test_update_task_attribute_node_id(self):
        tmp_node_id = 11
        payload = {'node_id': tmp_node_id}
        resp = self.app.put('/tasks/%s' % self.task_id,
                            content_type=self.content_type,
                            data=json.dumps(payload))
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['task']['node_id'], tmp_node_id)
        self.assertNotEquals(out['task']['node_id'], self.node_id)
        self.assertEquals(out['task']['action'], self.action)
        self.assertEquals(out['task']['payload'], self.payload)
        self.assertEquals(out['task']['state'], self.state)
        self.assertEquals(out['task']['result'], self.result)

        pass

    def test_update_task_attribute_action_TODO(self):
        pass

    def test_update_task_attribute_payload_TODO(self):
        pass

    def test_update_task_attribute_state_TODO(self):
        pass

    def test_update_task_attribute_result_TODO(self):
        pass

    def test_update_task_attribute_completed_TODO(self):
        pass

    def test_update_task_attribute_expires_TODO(self):
        pass

    def test_update_task_with_no_data_returns_a_400(self):
        resp = self.app.put('/tasks/%s' % self.task_id,
                            data=None,
                            content_type=self.content_type)
        self.assertEquals(resp.status_code, 400)


class TaskInvalidHTTPMethodTests(unittest2.TestCase):
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

    def test_405_returned_by_delete_on_tasks(self):
        self._execute_method('delete', '/tasks/', 405)

    def test_405_returned_by_patch_on_tasks(self):
        self._execute_method('patch', '/tasks/', 405)

    def test_405_returned_by_put_on_tasks(self):
        self._execute_method('put', '/tasks/', 405)

    def test_405_returned_by_post_on_tasks_with_id(self):
        self._execute_method('post', '/tasks/99', 405)

    def test_405_returned_by_patch_on_tasks_with_id(self):
        self._execute_method('patch', '/tasks/99', 405)
