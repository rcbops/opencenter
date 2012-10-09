#!/usr/bin/env python
import os
import logging
import chef

import backends


LOG = logging.getLogger('backend.driver')


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
            raise backends.BackendError

        self.role_map = {}

    def notify(self, object_type, notification_type, old_object, new_object):
        fn = getattr(self, "_%s_%s" % (object_type, notification_type))
        if fn:
            fn(old_object, new_object)

    def _node_update(old_object, new_object):
        if old_object['cluster'] != new_object['cluster']:
            _cluster_change(old_object, new_object)

    def _cluster_delete(old_object, new_object):
        if not self._cluster_exists(old_object['name']):
            raise backends.ClusterDoesNotExist

        env = chef.Environment(old_object['name'], self.api)
        env.delete()

    def _cluster_create(old_object, new_object):
        env = chef.Environment.create(new_object['name'],
                                      self.api,
                                      description=new_object['description'],
                                      override_attributes=new_object['config'])

        try:
            env.save()
        except chef.ChefServerError as e:
            raise backends.BackendError(e)

    def _cluster_update(old_object, new_object):
        if not self._cluster_exists(new_object['name']):
            raise backends.ClusterDoesNotExist

        env = chef.Environment(new_object['name'], self.api)
        if new_object['description']:
            env.description = new_object['description']

        if new_object['settings']:
            env.override_attributes = new_object['settings']
        env.save()

    def _cluster_change(old_object, new_object):
        if not self._cluster_exists(new_object['cluster']):
            raise backends.ClusterDoesNotExist

        if not self._host_exists(new_object['hostname']):
            raise backends.NodeDoesNotExist

        node = chef.Node(node, self.api)
        node.chef_environment = cluster
        node.save()

    def _cluster_exists(self, cluster_name):
        return self._entity_exists('environment', 'name', cluster_name)

    def _host_exists(self, host_name):
        return self._entity_exists('node', 'name', host_name)


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
