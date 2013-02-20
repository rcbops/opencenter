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

import roush
import roush.backends
# import roush.db.api


class NovaHaBackend(roush.backends.Backend):
    def __init__(self):
        super(NovaHaBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        # Commenting out for now, until loop logic is fixed
        #if action == 'add_backend':
        #    addl_constraints = []
        #    slave = "('chef-client' in facts.backends) and " \
        #            "(count(filter('nodes', " \
        #            "'facts.nova_role=\"nova-controller-master\"')) = 1) " \
        #            "and (facts.nova_role = none)"
        #    result = api._model_query('nodes', slave)
        #    if len(result) >= 1:
        #        addl_constraints.append(
        #            'facts.nova_role = "nova-controller-backup"')
        #    master = "('chef-client' in facts.backends) and " \
        #             "(count(filter('nodes', " \
        #             "'facts.nova_role=\"nova-controller-master\"')) = 0) " \
        #             "and (facts.nova_role = none)"
        #    result = api._model_query('nodes', master)
        #    if len(result) == 1:
        #        addl_constraints.append(
        #            'facts.nova_role = "nova-controller-master"')
        #    return addl_constraints
        if action == 'add_backend':
            return []

    def add_backend(self, state_data, api, node_id, **kwargs):
        reply_data = {}

        api.apply_expression(
            node_id,
            'facts.backends := union(facts.backends, "nova-ha")')

        #### BEGIN STUB ####
        # README(shep): Stubbing this in for now.. should be removed from
        #   here, and uncommented in additional_constraints above
        slave = "('chef-client' in facts.backends) and " \
                "(count(filter('nodes', " \
                "'facts.nova_role=\"nova-controller-master\"')) = 1) " \
                "and (facts.nova_role = none)"
        result = api._model_query('nodes', slave)
        if len(result) >= 1:
            api.apply_expression(
                node_id,
                'facts.nova_role := "nova-controller-backup"')

        master = "('chef-client' in facts.backends) and " \
                 "(count(filter('nodes', " \
                 "'facts.nova_role=\"nova-controller-master\"')) = 0) " \
                 "and (facts.nova_role = none)"
        result = api._model_query('nodes', master)
        if len(result) == 1:
            api.apply_expression(
                node_id,
                'facts.nova_role := "nova-controller-master"')
        #### END STUB ####
        return self._ok(data=reply_data)
