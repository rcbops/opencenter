#!/usr/bin/env python

import roush


class ChefClientBackend(roush.backends.Backend):
    def __init__(self):
        super(ChefClientBackend, self).__init__(__file__)

    def add_backend(self, api, node_id, **kwargs):
        self.logger.debug('adding chef-client backend')

        roush.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "chef-client")',
            api)

        return True
