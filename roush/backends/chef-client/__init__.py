#!/usr/bin/env python

import json
import os

import chef
import roush
import roush.backends
import mako.template


class ChefClientBackend(roush.backends.Backend):
    def __init__(self):
        super(ChefClientBackend, self).__init__(__file__)

    def _dict_merge(self, merge_target, new_dict):
        for key, value in new_dict.items():
            if isinstance(value, dict):
                if not key in merge_target:
                    merge_target[key] = {}
                merge_target[key] = self._dict_merge(
                    merge_target[key], new_dict[key])
            else:
                merge_target[key] = value

        return merge_target

    def _represent_node_attributes(self, api, node_id):
        node = api._model_get_by_id('nodes', node_id)

        # walk through all the facts and determine which are
        # cluster facts and which are node facts.  Generate templates
        # for each.

        node_attributes = {}
        cluster_attributes = {}

        if 'facts' in node:
            for fact in node['facts']:
                fact_info = roush.backends.fact_by_name(fact)

                if fact_info is None or 'cluster_wide' not in fact_info:
                    self.logger.debug('Invalid fact: %s' % fact)
                else:
                    if fact_info['cluster_wide'] is True:
                        if fact in cluster_attributes:
                            raise KeyError('fact already exists')

                        cluster_attributes[fact] = node['facts'][fact]
                    else:
                        if fact in node_attributes:
                            raise KeyError('fact already exists')

                        node_attributes[fact] = node['facts'][fact]

        # now generate the json from the facts
        environment_template = os.path.join(os.path.dirname(__file__),
                                            'environment.tmpl')
        node_template = os.path.join(os.path.dirname(__file__),
                                     'node.tmpl')

        chef_node_attrs = mako.template.Template(
            filename=node_template).render(facts=node_attributes)

        chef_env_attrs = mako.template.Template(
            filename=environment_template).render(facts=cluster_attributes)

        return (chef_node_attrs, chef_env_attrs)

    def converge_chef(self, api, node_id, **kwargs):
        # we are converging a node.  If the node is a container,
        # that probably implies converging all nodes under it.

        node = api._model_get_by_id('nodes', node_id)

        is_container = False

        if 'container' in node['facts']['backends']:
            is_container = True

        # generate node and environment settings
        node_attrs, env_attrs = self._represent_node_attributes(api, node_id)

        self.logger.debug('node: %s' % node_attrs)
        self.logger.debug('environment: %s' % env_attrs)
