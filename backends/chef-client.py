#!/usr/bin/env python
import os
import logging
import chef

import backends


LOG = logging.getLogger('backend.driver')


class ChefClient(backends.ConfigurationBackend):
    def __init__(self, config):
        LOG.debug('initializing chef backend')
        api = None
        self.config = config

        if 'knife_file' in self.config:
            api = chef.ChefAPI.from_config_file(self.config['knife_file'])
        else:
            api = chef.api.autoconfigure()

        if api:
            self.api = api
        else:
            raise backends.BackendError

        self.role_map = {}

    def notify(self, object_type, notification_type, old_object, new_object):
        pass


        # # load the role map
        # if 'role_location' in self.config:
        #     self._load_roles(self.config['role_location'])

    # def _load_roles(self, path):
    #     if os.path.isdir(path):
    #         self._load_role_directory(path)
    #     else:
    #         self._load_role_file(path)

    # def _load_role_directory(self, path):
    #     dirlist = os.listdir(path)
    #     for rel in dirlist:
    #         f = os.path.join(path, rel)

    #         if not os.path.isdir(f) and f.endswith(".map"):
    #             self._load_role_file(f)

    # def _load_role_file(self, path):
    #     with open(path, 'r') as f:
    #         for line in f:
    #             line = line.strip().split("#", 1)[0]
    #             if '=' in line:
    #                 key, roles = map(lambda x: x.strip(), line.split('='))
    #                 self.role_map[key] = map(
    #                     lambda x: x.strip(), roles.split(','))

    # def _entity_exists(self, entity, key, value):
    #     result = chef.Search(entity, '%s:%s' % (key, value), 1, 0, self.api)
    #     return len(result) == 1

    # def _cluster_exists(self, cluster_name):
    #     return self._entity_exists('environment', 'name', cluster_name)

    # def _host_exists(self, host_name):
    #     return self._entity_exists('node', 'name', host_name)

    # def get_cluster_settings(self, cluster_name):
    #     if not self._cluster_exists(cluster_name):
    #         raise backends.ClusterDoesNotExist

    #     return chef.Environment(cluster_name, self.api).override_attributes

    # def set_cluster_settings(self, cluster_name, cluster_desc=None,
    #                          cluster_settings=None):
    #     if not self._cluster_exists(cluster_name):
    #         raise backends.ClusterDoesNotExist

    #     env = chef.Environment(cluster_name, self.api)
    #     if cluster_desc is not None:
    #         env.description = cluster_desc
    #     if cluster_settings is not None:
    #         env.override_attributes = cluster_settings
    #     env.save()

    # def create_cluster(self, cluster_name, cluster_desc=None,
    #                    cluster_settings=None):
    #         env = chef.Environment.create(cluster_name,
    #                                       self.api,
    #                                       description=cluster_desc,
    #                                       override_attributes=cluster_
# s
# e
# t
# t
# i
# n
# g
# s
# )


    #         try:
    #             env.save()
    #         except chef.ChefServerError as e:
    #             raise backends.BackendError(e)

    # def delete_cluster(self, cluster_name):
    #     if not self._cluster_exists(cluster_name):
    #         raise backends.ClusterDoesNotExist

    #     env = chef.Environment(cluster_name, self.api)
    #     env.delete()

    # def list_clusters(self):
    #     env = chef.Search('environment', '*:*', 1000, 0, self.api)
    #     return [x['name'] for x in env]

    # def set_cluster_for_node(self, node, cluster):
    #     if not self._cluster_exists(cluster):
    #         raise backends.ClusterDoesNotExist

    #     if not self._host_exists(node):
    #         raise backends.NodeDoesNotExist

    #     node = chef.Node(node, self.api)
    #     node.chef_environment = cluster
    #     node.save()

    # def get_cluster_for_node(self, node):
    #     if not self._host_exists(node):
    #         raise backends.NodeDoesNotExist

    #     return chef.Node(node, self.api).chef_environment

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

    # def set_role_for_node(self, node, role):
    #     if not role in self.role_map:
    #         raise backends.RoleDoesNotExist

    #     if not self._host_exists(node):
    #         raise backends.RoleDoesNotExist

    #     node = chef.Node(node, self.api)
    #     node.run_list = self.role_map[role]
    #     node.save()

    # def  get_role_for_node(self, node):
    #     raise NotImplementedError
