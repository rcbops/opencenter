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
        raise NotImplementedError()

    def set_cluster_settings(self, cluster_name, settings):
        raise NotImplementedError()

    def create_cluster(self, cluster_name):
        raise NotImplementedError()

    def delete_cluster(self, cluster_name):
        raise NotImplementedError()

    def set_cluster_for_node(self, node, cluster):
        raise NotImplementedError()

    def get_cluster_for_node(self, node):
        raise NotImplementedError()

    def set_node_settings(self, node, settings):
        raise NotImplementedError()

    def get_node_status(self, node, settings):
        raise NotImplementedError()

    def delete_node(self, node):
        raise NotImplementedError()

    def get_node_settings(self, node):
        raise NotImplementedError()

    def set_role_for_node(self, node, role):
        raise NotImplementedError()

    def get_role_for_node(self, node):
        raise NotImplementedError()
