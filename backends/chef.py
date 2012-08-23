#!/usr/bin/env python

import logging

import backends

LOG = logging.getLogger('backend.driver')


class ChefBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing chef backend')
        self.config = config
