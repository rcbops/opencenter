#!/usr/bin/env python

from roush import backends


class TestBackend(backends.Backend):
    def __init__(self):
        super(TestBackend, self).__init__(__file__)

    def additional_constraints(self, api, action, ns):
        return []
