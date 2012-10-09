#!/usr/bin/env python

import logging

import backends

LOG = logging.getLogger('backend.driver')


class ChefServerBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing chef-server backend')

    def notify(self, object_type, notification_type, old_object, new_object):
        pass
