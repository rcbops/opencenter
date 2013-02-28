# vim: tabstop=4 shiftwidth=4 softtabstop=4
#               OpenCenter™ is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################
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
