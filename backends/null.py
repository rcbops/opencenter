#!/usr/bin/env python

import logging

import backends

LOG = logging.getLogger('backend.driver')


class NullBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing null backend')
        self.config = config
        self.roles = []
        self.cluster_for_node = {}
        self.cluster_settings = {}
        self.cluster_descriptions = {}
        self.node_settings = {}
        self.node_roles = {}

    def get_cluster_settings(self, cluster_name):
        return self.cluster_settings[cluster_name]

    def set_cluster_settings(self, cluster_name, cluster_desc=None,
                             cluster_settings=None):
        self.cluster_descriptions[cluster_name] = cluster_desc
        self.cluster_settings[cluster_name] = cluster_settings

    def create_cluster(self, cluster_name, cluster_desc=None,
                       cluster_settings=None):
        self.cluster_descriptions[cluster_name] = cluster_desc
        self.cluster_settings[cluster_name] = cluster_settings

    def delete_cluster(self, cluster_name):
        del self.cluster_settings[cluster_name]
        del self.cluster_descriptions[cluster_name]

    def list_clusters(self):
        return self.cluster_settings.keys()

    def set_cluster_for_node(self, node, cluster):
        self.cluster_for_node[node] = cluster

    def get_cluster_for_node(self, node):
        return self.cluster_for_node[node]

    def get_node_settings(self, node):
        return self.node_settings[node]

    def set_node_settings(self, node, settings):
        self.node_settings[node] = settings

    def create_node(self, node, role=None,
                    cluster=None, node_settings=None):
        self.node_settings[node] = node_settings
        self.cluster_for_node[node] = cluster

    def get_node_status(self, node):
        return True

    def delete_node(self, node):
        del self.node_settings[node]
        del self.cluster_for_node[node]

    def list_nodes(self):
        return self.node_settings.keys()

    def set_role_for_node(self, node, role):
        self.node_roles[node] = role
        if not role in self.roles:
            self.roles.append(role)

    def get_role_for_node(self, node):
        return self.node_roles[node]
