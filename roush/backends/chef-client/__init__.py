#!/usr/bin/env python

import roush


class ChefClientBackend(roush.backends.Backend):
    def __init__(self):
        super(ChefClientBackend, self).__init__(__file__)
