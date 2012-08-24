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

    def get_cluster_settings(self, cluster_name):
        # FIXME: raise on no environment
        return chef.Environment(cluster_name, self.api).override_attributes

    def set_cluster_settings(self, cluster_name, settings):
        # FIXME: raise on no environment
        env = chef.Environment(cluster_name, self.api)
        env.override_attributes = settings
        env.save()

    def create_cluster(self, cluster_name):
        env = chef.Environment(cluster_name, self.api)
        env.save()

    def delete_cluster(self, cluster_name):
        env = chef.Environment(cluster_name, self.api)
        env.delete()
