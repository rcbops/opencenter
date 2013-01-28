#!/usr/bin/env python

import copy
import time
import roush


class ChefEnvironmentBackend(roush.backends.Backend):
    def __init__(self):
        super(ChefEnvironmentBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, actions, ns):
        return []
