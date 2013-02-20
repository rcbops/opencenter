#!/usr/bin/env python

from roush import backends


class Test2Backend(backends.Backend):
    def __init__(self):
        super(Test2Backend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        if action == 'add_backend':
            node = api._model_get_by_id('nodes', node_id)
            parent_id = 1
            if 'parent_id' in node['facts']:
                parent_id = int(node['facts']['parent_id'])

            return ["facts.test2_fact = '%d'" % parent_id]

        return []

    def add_backend(self, state_data, api, node_id, **kwargs):
        return backends.primitive_by_name('node.add_backend')(
            state_data, api, node_id, backend='test2')
