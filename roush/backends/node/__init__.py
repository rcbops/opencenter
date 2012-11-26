#!/usr/bin/env python

import roush


class NodeBackend(roush.backends.Backend):
    def __init__(self):
        super(NodeBackend, self).__init__(__file__)
