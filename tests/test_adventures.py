# vim: tabstop=4 shiftwidth=4 softtabstop=4
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
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
from util import _test_request_returns, _test_seed_data_request_returns
from util import inject
from util import OpenCenterTestCase


class AdventuresTests(OpenCenterTestCase):
    base_object = 'adventure'


def build_tests():
    ats = inject(AdventuresTests)

    test = lambda self: _test_request_returns(
        self, 'post', '/%s/1/execute' % self._pluralize(self.base_object),
        {}, 400)
    test.__name__ = 'test_adventure_execute_no_node_returns_400'
    setattr(ats, test.__name__, test)

    test = lambda self: _test_seed_data_request_returns(
        self, 'post', '/%s/1/execute' % self._pluralize(self.base_object),
        {'node': 9999999}, 404, {self.base_object: 1})
    test.__name__ = 'test_adventure_execute_non_existant_node_returns_404'
    setattr(ats, test.__name__, test)

    test = lambda self: _test_seed_data_request_returns(
        self, 'post', '/%s/999999/execute' % self._pluralize(self.base_object),
        {'node': 1}, 404, {'node': 1})
    test.__name__ = 'test_adventure_execute_non_existant_adventure_returns_404'
    setattr(ats, test.__name__, test)

    return ats

AdventuresTests = build_tests()
