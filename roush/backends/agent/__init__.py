#!/usr/bin/env python

import copy
import time
import roush


class AgentBackend(roush.backends.Backend):
    def __init__(self):
        super(AgentBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, actions, ns):
        # this is probably a bit viscious.
        return ['"agent" in facts.backends']

    def add_backend(self, api, node_id, **kwargs):
        self.logger.debug('adding agent backend')

        roush.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "agent")', api)

        return True

    def run_task(self, api, node_id, **kwargs):
        action = kwargs.pop('action')
        payload = kwargs.pop('payload')

        adventure_globals = []

        # payload = dict([(x, kwargs[x]) for x in kwargs if x != 'action'])

        self.logger.debug('run_task: got kwargs %s' % kwargs)

        # push global variables
        if 'globals' in kwargs:
            adventure_globals = kwargs['globals']

        # run through the rest of the args and typecast them
        # as appropriate.
        node = api._model_get_by_id('nodes', node_id)
        typed_args = {}

        if 'roush_agent_actions' in node['attrs']:
            if action in node['attrs']['roush_agent_actions']:
                action_info = node['attrs']['roush_agent_actions'][action]
                typed_args = action_info['args']

        ns = copy.deepcopy(payload)
        ns.update(copy.deepcopy(adventure_globals))

        for k, v in kwargs.items():
            # we'll type these, if we know them, and cast them
            # appropriately.
            if k in typed_args:
                arg_info = typed_args[k]
                if arg_info['type'] == 'interface':  # cast this to a full node
                    v = api._model_get_by_id('nodes', v)
            ns[k] = v

        for k, v in payload.items():
            payload[k] = roush.webapp.ast.apply_expression(ns, v, api)

        task = api._model_create('tasks', {'node_id': node_id,
                                           'action': action,
                                           'payload': payload})

        self.logger.debug('added task as id %s' % task['id'])

        while task['state'] not in ['timeout', 'cancelled', 'done']:
            time.sleep(5)
            task = api._model_get_by_id('tasks', task['id'])

        if task['state'] != 'done':
            return False

        if 'result_code' in task['result'] and \
                task['result']['result_code'] == 0:
            # see if there are facts or attrs to apply.
            attrlist = task['result']['result_data'].get('attrs', {})
            factlist = task['result']['result_data'].get('facts', {})

            for attr, value in attrlist.iteritems():
                api._model_create('attrs', {'node_id': node_id,
                                            'key': attr,
                                            'value': value})

            for fact, value in factlist.iteritems():
                api._model_create('facts', {'node_id': node_id,
                                            'key': fact,
                                            'value': value})

            return True

        return False
