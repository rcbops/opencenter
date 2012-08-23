#!/usr/bin/env python

import logging

import backends

LOG=logging.getLogger('backend.driver')

class ChefBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        self.config=config

    def get_cluster_settings(self, cluster_name):
        LOG.debug('calling chef-backed "get_cluster_settings"')
