#!/usr/bin/env python

import time
import roush


class AgentBackend(roush.backends.Backend):
    def __init__(self):
        super(AgentBackend, self).__init__(__file__)

    def additional_constraints(self):
        # this is probably a bit viscious.
        return None

    def run_task(self, api, node_id, **kwargs):
        action = kwargs['action']
        # payload = kwargs['payload']
        payload = dict([(x, kwargs[x]) for x in kwargs if x != 'action'])

        task = api._model_create('tasks', {'node_id': node_id,
                                           'action': action,
                                           'payload': payload})

        self.logger.debug('added task as id %s' % task['id'])

        while task['state'] not in ['timeout', 'cancelled', 'done']:
            time.sleep(5)
            task = api._model_get_by_id('tasks', task['id'])

        return True
