# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import random
import string
import unittest2

from roush.db.database import init_db
from roush import webapp

from util import RoushTestCase, ScaffoldedTestCase


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class PlanInvalidPostTests(RoushTestCase):
    def setUp(self):
        self.content_type = 'application/json'

    def tearDown(self):
        pass

    def test_no_node_in_data(self):
        data = {'notnode': 99}
        resp = self.client.post('/plan/',
                                content_type=self.content_type,
                                data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['message'], 'no node specified')
        self.assertEquals(out['status'], 400)

    def test_no_plan_in_data(self):
        data = {'node': 99, 'notplan': {}}
        resp = self.client.post('/plan/',
                                content_type=self.content_type,
                                data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['message'], 'no plan specified')
        self.assertEquals(out['status'], 400)
