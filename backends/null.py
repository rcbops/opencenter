#!/usr/bin/env python

import logging

import backends

LOG = logging.getLogger('backend.driver')


class NullBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing null backend')
        self.config = config

    def get_cluster_settings(self, cluster_name):
        pass

    def set_cluster_settings(self, cluster_name, cluster_desc=None,
                             cluster_settings=None):
        pass

    def create_cluster(self, cluster_name, cluster_desc=None,
                       cluster_settings=None):
        pass

    def delete_cluster(self, cluster_name):
        pass

    def list_clusters(self):
        pass

    def set_cluster_for_node(self, node, cluster):
        pass

    def get_cluster_for_node(self, node):
        pass

    def get_node_settings(self, node):
        pass

    def set_node_settings(self, node, settings):
        pass

    def get_node_status(self, node):
        pass

    def delete_node(self, node):
        pass

    def list_nodes(self):
        pass

    def set_role_for_node(self, node, role):
        pass

    def get_role_for_node(self, node):
        pass
