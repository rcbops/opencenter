#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import os
import StringIO

import chef
import roush
import roush.backends
import time
import mako.template


class ChefClientBackend(roush.backends.Backend):
    def __init__(self):
        super(ChefClientBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        if action == 'add_backend':
            return None
        return []

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

        return (json.loads(chef_node_attrs), json.loads(chef_env_attrs))

    def _entity_exists(self, entity_type, key, value, chef_api):
        result = chef.Search(entity_type, '%s:%s' % (key, value),
                             1, 0, chef_api)
        return len(result) == 1

    def _environment_exists(self, environment_name, chef_api):
        return self._entity_exists('environment', 'name',
                                   environment_name, chef_api)

    def _node_exists(self, node_name, chef_api):
        return self._entity_exists('node', 'name',
                                   node_name, chef_api)

    def _map_roles(self, role):
        if role == 'nova-compute':
            return ['role[single-compute]']
        elif role == 'nova-infra':
            return ['role[single-controller]']
        elif role == 'nova-controller1':
            return ['role[ha-controller1]']
        elif role == 'nova-controller2':
            return ['role[ha-controller2]']
        return []

    def _expand_nodelist(self, nodelist, api):
        """
        given a list of nodes (including containers),
        generate a fully expanded list of non-container-y
        nodes
        """

        final_nodelist = []

        self.logger.debug('nodelist: %s' % nodelist)

        for node_id in nodelist:
            node = api.node_get_by_id(node_id)
            is_container = False
            if 'backends' in node['facts'] and \
                    'container' in node['facts']['backends']:
                is_container = True

            if not is_container:
                final_nodelist.append(node_id)
            else:
                query = 'facts.parent_id = %s' % node_id
                child_nodes = api.nodes_query(query)
                child_node_ids = [x['id'] for x in child_nodes]

                final_nodelist += self._expand_nodelist(child_node_ids, api)

        return final_nodelist

    def _get_nodes_in_env(self, env):
        """
        given a chef environment, find all nodes with that environment
        in their facts and return a list of node ids. Exclude containers
        """

        final_nodelist = []

        self.logger.debug('environment: %s' % env)

        query = 'facts.chef_environment = %s' % env
        nodelist = api.nodes_query(query)

        for node in nodelist:
            is_container = False
            if 'backends' in node['facts'] and \
                    'container' in node['facts']['backends']:
                is_container = True

            if not is_container:
                node_id = node['id']
                final_nodelist.append(node_id)

        return final_nodelist

    def _serialize_node_blob(self, blob):
        result = {}
        for key, value in blob.items():
            if isinstance(value, chef.node.NodeAttributes):
                result[key] = self._serialize_node_blob(value)
            else:
                result[key] = value
        return result

    def converge_chef(self, state_data, api, node_id, **kwargs):
        def safe_get_fact(node, fact):
            if not fact in node['facts']:
                return None

            return node['facts'][fact]

        def verify_facts(node, facts):
            for fact in facts:
                if not fact in node['facts']:
                    return False

            return True

        # we are converging a node.  If the node is a container,
        # that probably implies converging all nodes under it.
        self.logger.info('Converging node %s via chef-client backend' % (
            node_id,))

        node = api._model_get_by_id('nodes', node_id)

        if not 'chef_server_consumed' in node['facts']:
            return self._fail(msg='missing fact: chef_server_consumed')

        chef_server_consumed = node['facts']['chef_server_consumed']
        cs = api._model_get_by_id('nodes', chef_server_consumed)

        if not cs:
            return self._fail(msg='cannot find consumed chef server')

        if not verify_facts(cs, ['chef_server_uri',
                                 'chef_server_client_name',
                                 'chef_server_client_pem']):
            return self._fail(msg='chef server missing chef attrs')

        chef_server_uri = cs['facts']['chef_server_uri']
        chef_server_client_name = cs['facts']['chef_server_client_name']
        chef_server_client_pem = cs['facts']['chef_server_client_pem']

        self.logger.debug('Creating connection to chef server')

        # make a chef api object
        pem = StringIO.StringIO(chef_server_client_pem)
        rsa_key = chef.rsa.Key(pem)

        chef_api = chef.ChefAPI(chef_server_uri,
                                rsa_key,
                                chef_server_client_name)
        pem.close()

        if not 'chef_environment' in node['facts']:
            # this node has been pulled out of a chef environment.
            # this is hateful, but...
            api.apply_expression(node_id, 'facts.backends := '
                                 'remove(facts.backends, "chef-client")')

            if self._node_exists(node['name'], chef_api):
                chef_node = chef.Node(node['name'], chef_api)
                chef_node.delete()

            return self._ok()

        # generate node and environment settings
        node_attrs, env_attrs = self._represent_node_attributes(api, node_id)

        self.logger.debug('node: %s' % node_attrs)
        self.logger.debug('environment: %s' % env_attrs)

        nova_role = node['facts']['nova_role']
        chef_environment = node['facts']['chef_environment'].replace(' ', '_')

        # create the environment if it does not exist
        env = None

        if not self._environment_exists(chef_environment, chef_api):
            self.logger.debug('Creating non-existent environment: %s' %
                              chef_environment)

            env = chef.Environment.create(chef_environment,
                                          api=chef_api)
            env.save()
        else:
            env = chef.Environment(chef_environment, chef_api)

        if env is None:
            self.logger.error('Cannot find/create chef environment')
            return self._fail()

        old_env_overrides = env.override_attributes

        self.logger.debug('Old environment overrides: %s' % old_env_overrides)

        # Find the node.  Sometimes chef takes a while to index; we will retry
        for i in range(3):
            if self._node_exists(node['name'], chef_api):
                break
            else:
                self.logger.info("Node '%s' is not registered with chef"
                                 "server.  Retrying %s/3)" % (
                                     node['name'], i + 1))
                time.sleep(10)
            if i == 3:
                msg = ("Node '%s' is not registered to chef.  "
                       "Exceeded max retries" % node['name'])
                self.logger.error(msg)
                return self._fail(msg=msg)

        chef_node = chef.Node(node['name'], chef_api)
        old_node_overrides = self._serialize_node_blob(chef_node.override)

        self.logger.debug('Old node overrides: %s' % old_node_overrides)

        # we'll always converge node, just to be sure
        need_node_converge = False
        need_env_converge = False

        query = '"adventurator" in attrs.roush_agent_output_modules'
        adventurator = api._model_get_first_by_query('nodes', query)
        if not adventurator:
            self.logger.error('Could not find adventurator')
            return self._fail(msg='could not find adventurator')

        # we'll always stomp this stuff..

        # if old_node_overrides != node_attrs or \
        #         chef_node.chef_environment != chef_environment or\
        #         chef_node.run_list != self._map_roles(nova_role):
        self.logger.debug('Updating chef node')
        #need_node_converge = True
        self.logger.debug('Setting environment to %s' % chef_environment)
        chef_node.chef_environment = chef_environment
        chef_node.override = node_attrs
        old_runlist = chef_node.run_list
        chef_node.run_list = self._map_roles(nova_role)
        chef_node.save()

        if old_runlist != chef_node.run_list:
            # roles changed, refresh node and then all other nodes in env
            need_node_converge = True

        if old_env_overrides != env_attrs:
            # refresh entire environment in one go
            self.logger.debug('Updating environment')
            need_env_converge = True
            env.override_attributes = env_attrs
            env.save()

        if need_node_converge:
            # first run converge on the node in question
            self.logger.debug('chef updating node: %s' % node_id)
            dsl = [{'primitive': 'run_chef', 'ns': {}}]
            node_task = api._model_create(
                'tasks',
                {'action': 'adventurate',
                'node_id': adventurator['id'],
                'payload': {'nodes': [node_id],
                'adventure_dsl': dsl}})

            # watch for task state
            while node_task['state'] not in ['timeout', 'cancelled', 'done']:
                time.sleep(5)
                node_task = api._model_get_by_id('tasks', node_task['id'])

            if node_task['state'] != 'done':
                return self._fail(msg='task did not finish successfully')

            if 'result_code' in node_task['result'] and \
                    node_task['result']['result_code'] == 0:
                # now converge the rest of the nodes in the environment
               # nodelist = self._expand_nodelist([node_id], api)
                nodelist = self._get_nodes_in_env(chef_environment)
                if node_id in nodelist:
                    nodelist.remove(node_id)
                self.logger.debug('chef updating nodes: %s' % nodelist)
                # now converge the affected nodes
                if len(nodelist) > 0:
                    all_task = api._model_create(
                        'tasks',
                        {'action': 'adventurate',
                        'node_id': adventurator['id'],
                        'payload': {'nodes': nodelist,
                        'adventure_dsl': dsl}})

                    # watch for task state
                    while all_task['state'] not in \
                            ['timeout', 'cancelled', 'done']:
                        time.sleep(5)
                        all_task = api._model_get_by_id(
                            'tasks', all_task['id'])

                    if all_task['state'] != 'done':
                        return self._fail(
                            msg='task did not finish successfully')

                    if 'result_code' in node_task['result'] and \
                            node_task['result']['result_code'] == 0:
                        return self._ok()

            return self._fail(msg='task did not finish successfully')

        elif need_env_converge:
            # converge ALL of the nodes
            nodelist = self._expand_nodelist([node_id], api)
            self.logger.debug('chef updating nodes: %s' % nodelist)
            # now converge the affected nodes
            if len(nodelist) > 0:
                all_task = api._model_create(
                    'tasks',
                    {'action': 'adventurate',
                    'node_id': adventurator['id'],
                    'payload': {'nodes': nodelist,
                    'adventure_dsl': dsl}})

                # watch for task state
                while all_task['state'] not in \
                        ['timeout', 'cancelled', 'done']:
                    time.sleep(5)
                    all_task = api._model_get_by_id(
                        'tasks', all_task['id'])

                if all_task['state'] != 'done':
                    return self._fail(
                        msg='task did not finish successfully')

                if 'result_code' in node_task['result'] and \
                        node_task['result']['result_code'] == 0:
                    return self._ok()

                return self._fail(msg='task did not finish successfully')

    def add_backend(self, api, node_id, **kwargs):
        return self._fail(msg='backend added by install_chef')
