#!/usr/bin/env python
import logging
import chef

import backends

LOG = logging.getLogger('backend.driver')


class OpscodechefBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing chef backend')
        api = None
        self.config = config


        print self.config

        if 'knife_file' in self.config:
            api = chef.ChefAPI.from_config_file(self.config['knife_file'])
        else:
            api = chef.api.autoconfigure()

        if api:
            self.api = api
        else:
            raise BackendError

    def _entity_exists(self, entity, key, value):
        result = chef.Search(entity, '%s:%s' % (key, value), 1, 0, self.api)
        return len(result) == 1

    def _cluster_exists(self, cluster_name):
        return self._entity_exists('environment', 'name', cluster_name)

    def _host_exists(self, host_name):
        return self._entity_exists('node', 'name', host_name)

    def get_cluster_settings(self, cluster_name):
        if not self._cluster_exists(cluster_name):
            raise ClusterDoesNotExist

        return chef.Environment(cluster_name, self.api).override_attributes

    def set_cluster_settings(self, cluster_name, settings):
        if not self._cluster_exists(cluster_name):
            raise ClusterDoesNotExist

        env = chef.Environment(cluster_name, self.api)
        env.override_attributes = settings
        env.save()

    def create_cluster(self, cluster_name):
        env = chef.Environment(cluster_name, self.api)
        env.save()

    def delete_cluster(self, cluster_name):
        if not self._cluster_exists(cluster_name):
            raise ClusterDoesNotExist

        env = chef.Environment(cluster_name, self.api)
        env.delete()

    def list_clusters(self):
        env = chef.Search('environment', '*:*', 1000, 0, self.api)
        return [ x['name'] for x in env ]

    def set_cluster_for_node(self, node, cluster):
        if not self._cluster_exists(cluster):
            raise ClusterDoesNotExist

        if not self._host_exists(node):
            raise NodeDoesNotExist

        node = chef.Node(node, self.api)
        node.chef_environment = cluster
        node.save()

    def get_cluster_for_node(self, node):
        if not self._host_exists(node):
            raise NodeDoesNotExist

        return chef.Node(node, self.api).chef_environment

    def get_node_settings(self, node):
        if not self._host_exists(node):
            raise NodeDoesNotExist

        return chef.Node(node, self.api).override

    def set_node_settings(self, node, settings):
        if not self._host_exists(node):
            raise NodeDoesNotExist

        node = chef.Node(node, self.api)
        node.override = settings
        node.save()

    def get_node_status(self, node):
        if not self._host_exists(node):
            raise NodeDoesNotExist

        # What does this do?!?!
        return True

    def delete_node(self, node):
        if not self._host_exists(node):
            raise NodeDoesNotExist

        node = chef.Node(node, self.api)
        node.delete

    def list_nodes(self):
        env = chef.Search('node', '*:*', 1000, 0, self.api)
        return [ x['name'] for x in env ]

    def set_role_for_node(self, node, role):
        raise NotImplementedError

    def  get_role_for_node(self, node):
        raise NotImplementedError
