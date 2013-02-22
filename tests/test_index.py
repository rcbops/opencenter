# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import random

from opencenter.db.database import init_db
from opencenter import webapp

from util import OpenCenterTestCase, ScaffoldedTestCase


class IndexTest(OpenCenterTestCase):
    def setUp(self):
        self.content_type = 'application/json'

    def tearDown(self):
        pass

    def test_get_index(self):
        resp = self.client.get('/',
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertTrue('url' in out)
        self.assertIsInstance(out['resources'], dict)
        resources = ['adventures', 'attrs', 'facts', 'filters',
                     'primitives', 'nodes', 'tasks']
        for resource in resources:
            self.assertTrue(resource in out['resources'])
            self.assertTrue('url' in out['resources'][resource])
