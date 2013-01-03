#!/usr/bin/env python

import roush


class ChefServerBackend(roush.backends.Backend):
    def __init__(self):
        super(ContainerBackend, self).__init__(__file__)
