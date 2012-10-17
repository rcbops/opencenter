#!/usr/bin/env python

import logging

import backends

LOG = logging.getLogger('backend.driver.chef-server')


class ChefServerBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing chef-server backend')

    def notify(self, otype, ntype, old_object, new_object):
        LOG.debug('chef-server: got %s for %s' % (ntype, otype))
        pass
