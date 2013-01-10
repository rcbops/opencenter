#!/usr/bin/env python

import copy
import time
import roush


class AgentBackend(roush.backends.Backend):
    def __init__(self):
        super(AgentBackend, self).__init__(__file__)

    def additional_constraints(self):
        # this is probably a bit viscious.
        return None

    def add_backend(self, api, node_id, **kwargs):
        self.logger.debug('adding agent backend')

        roush.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "agent")', api)

        return True

    def run_task(self, api, node_id, **kwargs):
        action = kwargs['action']
        payload = kwargs['payload']
        adventure_globals = []

        # payload = dict([(x, kwargs[x]) for x in kwargs if x != 'action'])

        self.logger.debug('run_task: got kwargs %s' % kwargs)

        # push global variables, unless they have been specifically
        # set in the task payload.
        if 'globals' in kwargs:
            adventure_globals = kwargs['globals']
            # for k, v in globals.items():
            #     if not k in payload:
            #         payload[k] = v

        ns = copy.deepcopy(payload)
        ns.update(copy.deepcopy(adventure_globals))

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
