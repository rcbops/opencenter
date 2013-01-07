#!/usr/bin/env python

import roush


class NovaBackend(roush.backends.Backend):
    def __init__(self):
        super(NovaBackend, self).__init__(__file__)
