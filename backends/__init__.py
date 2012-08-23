#!/usr/bin/env python

import sys
import logging

LOG = logging.getLogger('backend.driver')


def load(name, config={}):
    # expects an include of backends/#{name}.py,
    # with a class of #{name.capitalize}Backend

    import_str = "backends.%s" % name
    class_str = "%sBackend" % name.capitalize()

    __import__(import_str)
    return getattr(sys.modules[import_str], class_str)(config)


class ConfigurationBackend(object):
    def get_cluster_settings(self, cluster_name):
        LOG.debug('Calling unimplemented function "get_cluster_settings"')
        raise NotImplementedError()

    def set_cluster_settings(self, cluster_name, settings):
        LOG.debug('Calling unimplemented function "set_cluster_settings"')
        raise NotImplementedError()

    def get_node_settings(self, node_name):
        LOG.debug('Calling unimplemented function "get_node_settings"')
        raise NotImplementedError()

    def set_node_settings(self, node_name, settings):
        LOG.debug('Calling unimplemented function "set_node_settings"')
        raise NotImplementedError()

    def add_node_to_cluster(self, node_name, cluster_name):
        LOG.debug('Calling unimplemented function "add_node_to_cluster"')
        raise NotImplementedError()

    def set_node_role(self, node_name, role_name):
        LOG.debug('Calling unimplemented function "set_node_role"')
        raise NotImplementedError()
