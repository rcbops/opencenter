#!/usr/bin/env python

import roush


class ChefServerBackend(roush.backends.Backend):
    def __init__(self):
        super(ChefServerBackend, self).__init__(__file__)

    def add_backend(self, api, node_id, **kwargs):
        self.logger.debug('adding chef-server backend')

        roush.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "chef-server")',
            api)

        return True
