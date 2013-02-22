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

# import copy
import time
import opencenter


class AgentBackend(opencenter.backends.Backend):
    def __init__(self):
        super(AgentBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, actions, ns):
        # this is probably a bit viscious.
        return []

    def run_task(self, state_data, api, node_id, **kwargs):
        action = kwargs.pop('action')
        payload = kwargs.pop('payload')
        parent_task_id = None
        reply_data = {}

        adventure_globals = {}

        node = api._model_get_by_id('nodes', node_id)
        rollback_action = 'rollback_%s' % action
        if 'opencenter_agent_actions' in node['attrs'] and \
                rollback_action in node['attrs']['opencenter_agent_actions']:
            reply_data['rollback'] = {'primitive': rollback_action,
                                      'ns': {}}

        # payload = dict([(x, kwargs[x]) for x in kwargs if x != 'action'])

        # push global variables
        # if 'globals' in kwargs:
        #     adventure_globals = kwargs.pop('globals')
        #     parent_task_id = adventure_globals.get('parent_task_id', None)

        if payload is not None and 'globals' in payload:
            parent_task_id = payload['globals'].get('parent_task_id', None)

        # run through the rest of the args and typecast them
        # as appropriate.
        # node = api._model_get_by_id('nodes', node_id)

        # typed_args = {}

        # if 'opencenter_agent_actions' in node['attrs']:
        #     if action in node['attrs']['opencenter_agent_actions']:
        #         action_info =
        #           node['attrs']['opencenter_agent_actions'][action]
        #         typed_args = action_info['args']

        # ns = copy.deepcopy(payload)
        # ns.update(copy.deepcopy(adventure_globals))

        # for k, v in kwargs.items():
        #     # we'll type these, if we know them, and cast them
        #     # appropriately.
        #     if k in typed_args:
        #         arg_info = typed_args[k]
        #         if arg_info['type'] == 'interface':  # make full node
        #             v = api._model_get_by_id('nodes', v)
        #     ns[k] = v

        # for k, v in payload.items():
        #     payload[k] = opencenter.webapp.ast.apply_expression(ns, v, api)

        # for k, v in kwargs.items():
        #     payload[k] = v

        for k, v in adventure_globals.items():
            if not k in payload:
                payload[k] = v

        task_data = {'node_id': node_id,
                     'action': action,
                     'payload': payload}

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
                    action_info =
                    node['attrs']['opencenter_agent_actions'][action]

                    direct_cons = action_info.get('consequences', [])

                    for dcon in direct_cons:
                        concrete = api.concrete_expression(dcon, payload)
                        conslist += [concrete]

            for cons in conslist:
                api.apply_expression(node_id, cons)

            return self._ok(data=reply_data)

        return self._fail(msg='Task failed')
