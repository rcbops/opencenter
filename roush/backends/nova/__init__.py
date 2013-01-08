#!/usr/bin/env python

import roush


class NovaBackend(roush.backends.Backend):
    def __init__(self):
        super(NovaBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        if action == 'add_backend':
            return ['"chef-client" in facts.backends']

    def add_backend(self, api, node_id, **kwargs):
        self.logger.debug('adding nova backend')

        roush.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "nova")', api)

        return True
