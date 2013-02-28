#!/usr/bin/env python
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
from opencenter import backends


class TestBackend(backends.Backend):
    def __init__(self):
        super(TestBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        # this is a special-case set_fact that only sets the
        # fact "unsettable_fact"
        if action == 'set_test_fact':
            if ns['key'] != 'unsettable_fact':
                return None
            return ['"test" in facts.backends']

        return []

    def set_test_fact(self, state_data, api, node_id, **kwargs):
        return opencenter.backends.primitive_by_name('node.set_fact')(
            state_data, api, node_id, **kwargs)
