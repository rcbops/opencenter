#!/usr/bin/env python

import json
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

                print "fact: %s => %s" % (fact, fact_info)

                # print fact_info

                fact_template = roush.backends.backend_by_name(
                    fact_info['backend']).fact_template(fact, 'chef-client')

                # print "fact_template: %s" % fact_template

                if fact_template:
                    snippet = mako.template.Template(
                        fact_template).render(node=node,
                                              key=fact,
                                              value=node['facts'][fact])

                    json_snippet = json.loads(snippet)

                    # print "fact: %s => %s" % (fact, snippet)
                    if fact_info['cluster_wide'] is True:
                        if fact in cluster_attributes:
                            raise KeyError('fact already exists')

                        cluster_attributes[fact] = json_snippet
                    else:
                        if fact in node_attributes:
                            raise KeyError('fact already exists')

                        node_attributes[fact] = json_snippet

            # Now we have a list of cluster attributes and node
            # attributes.  Let's merge them all together and
            # push them to the chef server.
            chef_node_attrs = {}
            chef_env_attrs = {}

            for snippet in node_attributes:
                chef_node_attrs = self._dict_merge(chef_node_attrs,
                                                   node_attributes[snippet])

            for snipper in cluster_attributes:
                chef_env_attrs = self._dict_merge(chef_env_attrs,
                                                  cluster_attributes[snipper])

            print "node: %s" % chef_node_attrs
            print "env : %s" % chef_env_attrs
