#!/usr/bin/env python

from roush import backends


class TestBackend(backends.Backend):
    def __init__(self):
        super(TestBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        # this is a special-case set_fact that only sets the
        # fact "unsettable_fact"
        if action == 'set_test_fact':
            if ns['key'] != 'unsettable_fact':
                return None
            return ['"test" in facts.backends']

        return []

    def set_test_fact(self, state_data, api, node_id, **kwargs):
        return roush.backends.fact_by_name('node.set_fact')(
            state_data, api, node_id, **kwargs)
