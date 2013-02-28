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

import time
import opencenter


class AgentBackend(opencenter.backends.Backend):
    def __init__(self):
        super(AgentBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, actions, ns):
        # this is probably a bit viscious.
        return []

    # README(shep): Not executed by the server, skipping from code coverage
    def run_task(self, state_data, api, node_id, **kwargs):  # pragma: no cover
        action = kwargs.pop('action')
        payload = kwargs.pop('payload')
        timeout = kwargs.get('timeout', 30)
        parent_task_id = None
        reply_data = {}

        adventure_globals = {}

        node = api._model_get_by_id('nodes', node_id)
        rollback_action = 'rollback_%s' % action
        if 'opencenter_agent_actions' in node['attrs'] and \
                rollback_action in node['attrs']['opencenter_agent_actions']:
            reply_data['rollback'] = {'primitive': rollback_action,
                                      'ns': {}}

        if payload is not None and 'globals' in payload:
            parent_task_id = payload['globals'].get('parent_task_id', None)

        for k, v in adventure_globals.items():
            if not k in payload:
                payload[k] = v

        task_data = {'node_id': node_id,
                     'action': action,
                     'payload': payload,
                     'expires': int(time.time() + timeout)}

        if parent_task_id is not None:
            task_data['parent_id'] = parent_task_id

        task = api._model_create('tasks', task_data)

        self.logger.debug('added task as id %s' % task['id'])

        while task['state'] not in ['timeout', 'cancelled', 'done']:
            time.sleep(5)
            task = api._model_get_by_id('tasks', task['id'])

        if task['state'] != 'done':
            return self._fail(msg='task did not finish successfully')

        if 'result_code' in task['result'] and \
                task['result']['result_code'] == 0:
            # apply any consequences
            conslist = task['result']['result_data'].get('consequences', [])

            # find out and register the consequences of the task that the
            # agent is advertising.

            node = api._model_get_by_id('nodes', node_id)
            if 'opencenter_agent_actions' in node['attrs']:
                if action in node['attrs']['opencenter_agent_actions']:
                    agent_actions = 'opencenter_agent_actions'
                    action_info = node['attrs'][agent_actions][action]

                    direct_cons = action_info.get('consequences', [])

                    for dcon in direct_cons:
                        concrete = api.concrete_expression(dcon, payload)
                        conslist += [concrete]

            for cons in conslist:
                api.apply_expression(node_id, cons)

            return self._ok(data=reply_data)

        return self._fail(msg='Task failed')
