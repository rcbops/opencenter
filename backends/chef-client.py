#!/usr/bin/env python
import logging
import os
import sys
import traceback

import chef

import backends

# FIXME: the eventing should pass through the interesting things
from db import api as dbapi

LOG = logging.getLogger('backend.driver.chef-client')


class ChefClientBackend(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing chef-client backend')
        api = None
        self.config = config

        if 'knife_file' in self.config:
            api = chef.ChefAPI.from_config_file(self.config['knife_file'])
        else:
            api = chef.api.autoconfigure()

        if api:
            self.api = api
        else:
            raise backends.BackendError('cannot initialize api')

        self.role_map = {}

        if 'role_location' in self.config:
            self._load_roles(self.config['role_location'])

    def _load_roles(self, path):
        if os.path.isdir(path):
            self._load_role_directory(path)
        else:
            self._load_role_file(path)

    def _load_role_directory(self, path):
        dirlist = os.listdir(path)
        for rel in dirlist:
            f = os.path.join(path, rel)

            if not os.path.isdir(f) and f.endswith(".map"):
                self._load_role_file(f)

    def _load_role_file(self, path):
        with open(path, 'r') as f:
            for line in f:
                line = line.strip().split("#", 1)[0]
                if '=' in line:
                    key, roles = map(lambda x: x.strip(), line.split('='))
                    self.role_map[key] = map(
                        lambda x: x.strip(), roles.split(','))

    def notify(self, otype, ntype, old_object, new_object):
        fn = None
        LOG.debug('chef-client: got %s for %s' % (ntype, otype))

        try:
            fn = getattr(self, "_%s_%s" % (otype, ntype))
        except AttributeError:
            pass

        if fn:
            LOG.debug('chef-client: dispatching to handler')
            fn(old_object, new_object)

    def _node_update(self, old_object, new_object):
        if old_object['cluster_id'] != new_object['cluster_id']:
            self.change_node_cluster(old_object, new_object)
        if old_object['role'] != new_object['role']:
            self.change_node_role(old_object, new_object)

    def _cluster_delete(self, old_object, new_object):
        if not self._cluster_exists(old_object['name']):
            raise backends.ClusterDoesNotExist(
                'cluster %s does not exist' % old_object['name'])

        env = chef.Environment(old_object['name'], self.api)
        env.delete()

    def _cluster_create(self, old_object, new_object):
        env = chef.Environment.create(new_object['name'],
                                      self.api,
                                      description=new_object['description'],
                                      override_attributes=new_object['config'])

        env.save()

    def _cluster_update(self, old_object, new_object):
        if not self._cluster_exists(new_object['name']):
            raise backends.ClusterDoesNotExist(
                'cluster %s does not exist' % new_object['name'])

        env = chef.Environment(new_object['name'], self.api)
        if new_object['description']:
            env.description = new_object['description']

        if new_object['settings']:
            env.override_attributes = new_object['settings']
        env.save()

    def change_node_role(self, old_object, new_object):
        if new_object['role'] and new_object['backend'] == 'chef-client':
            if not new_object['role'] in self.role_map:
                raise backends.RoleDoesNotExist(new_object['role'])

            if not self._host_exists(new_object['hostname']):
                raise backends.NodeDoesNotExist(new_object['hostname'])

            node = chef.Node(new_object['hostname'], self.api)
            node.run_list = self.role_map[new_object['role']]
            node.save

    def change_node_cluster(self, old_object, new_object):
        new_cluster_name = '_default'

        if new_object['cluster_id'] and new_object['backend'] == 'chef-client':
            c = dbapi._model_get_by_id('clusters', new_object['cluster_id'])
            new_cluster_name = c['name']

        if not self._cluster_exists(new_cluster_name):
            raise backends.ClusterDoesNotExist(
                'cluster %s does not exist' % new_cluster_name)

        if not self._host_exists(new_object['hostname']):
            raise backends.NodeDoesNotExist(
                'node %s does not exist' % new_object['hostname'])

        node = chef.Node(new_object['hostname'], self.api)
        node.chef_environment = new_cluster_name
        node.save()

    def _cluster_exists(self, cluster_name):
        return self._entity_exists('environment', 'name', cluster_name)

    def _host_exists(self, host_name):
        return self._entity_exists('node', 'name', host_name)

    def _entity_exists(self, entity, key, value):
        result = chef.Search(entity, '%s:%s' % (key, value), 1, 0, self.api)
        return len(result) == 1

        # # load the role map

    # def get_node_settings(self, node):
    #     if not self._host_exists(node):
    #         raise backends.NodeDoesNotExist

    #     return chef.Node(node, self.api).override

    # def set_node_settings(self, node, settings):
    #     if not self._host_exists(node):
    #         raise backends.NodeDoesNotExist

    #     node = chef.Node(node, self.api)
    #     node.override = settings
    #     node.save()

    # def create_node(self, node, role=None,
    #                 cluster=None, node_settings=None):
    #     pass

    # def get_node_status(self, node):
    #     if not self._host_exists(node):
    #         raise backends.NodeDoesNotExist

    #     # What does this do?!?!
    #     return True

    # def delete_node(self, node):
    #     if not self._host_exists(node):
    #         raise backends.NodeDoesNotExist

    #     node = chef.Node(node, self.api)
    #     node.delete

    # def list_nodes(self):
    #     env = chef.Search('node', '*:*', 1000, 0, self.api)
    #     return [x['name'] for x in env]
