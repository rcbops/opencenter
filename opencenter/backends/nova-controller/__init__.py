#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import opencenter
import opencenter.backends
# import opencenter.db.api


class NovaControllerBackend(opencenter.backends.Backend):
    def __init__(self):
        super(NovaControllerBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        return []

    def add_backend(self, state_data, api, node_id, **kwargs):
        return opencenter.backends.primitive_by_name('node.add_backend')(
            state_data, api, node_id, backend='nova-controller')
