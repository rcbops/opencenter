#!/usr/bin/env python

import logging

import backends

LOG = logging.getLogger(__name__)


class UnprovisionedBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing unprovisioned backend')

    def notify(self, otype, ntype, old_object, new_object):
        LOG.debug('Unprov: got %s for %s' % (ntype, otype))
