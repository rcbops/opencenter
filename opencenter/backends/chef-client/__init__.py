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
import opencenter
import opencenter.backends
import time
import mako.template


class ChefClientBackend(opencenter.backends.Backend):
    def __init__(self):
        super(ChefClientBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        if action == 'add_backend':
            return None
        return []

    # README(shep): not executed on the server, skipping from code coverage
    def _represent_node_attributes(self, api, node_id):  # pragma: no cover
        node = api._model_get_by_id('nodes', node_id)

        # walk through all the facts and determine which are
        # cluster facts and which are node facts.  Generate templates
        # for each.

        node_attributes = {}
        cluster_attributes = {}

        if 'facts' in node:
            for fact in node['facts']:
                fact_info = opencenter.backends.fact_by_name(fact)

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

    # README(shep): not executed on the server, skipping from code coverage
    def _entity_exists(self, entity_type, key,
                       value, chef_api):  # pragma: no cover
        result = chef.Search(entity_type, '%s:%s' % (key, value),
                             1, 0, chef_api)
        return len(result) == 1

    # README(shep): not executed on the server, skipping from code coverage
    def _environment_exists(self, environment_name,
                            chef_api):  # pragma: no cover
        return self._entity_exists('environment', 'name',
                                   environment_name, chef_api)

    # README(shep): not executed on the server, skipping from code coverage
    def _node_exists(self, node_name, chef_api):  # pragma: no cover
        return self._entity_exists('node', 'name',
                                   node_name, chef_api)

    # README(shep): not executed on the server, skipping from code coverage
    def _map_roles(self, role):  # pragma: no cover
        if role == 'nova-compute':
            return ['role[single-compute]']
        elif role == 'nova-infra':
            return ['role[single-controller]']
        elif role == 'nova-controller-master':
            return ['role[ha-controller1]']
        elif role == 'nova-controller-backup':
            return ['role[ha-controller2]']
            # Debug to work around glance ha issue
            #role_list = ['role[base]', 'role[mysql-master]',
            #             'role[rabbitmq-server]', 'role[keystone-api]',
            #             'role[nova-scheduler]', 'role[nova-api-ec2]',
            #             'role[nova-api-os-compute]', 'role[cinder-api]',
            #             'role[cinder-scheduler]', 'role[nova-cert]',
            #             'role[nova-vncproxy]', 'role[horizon-server]',
            #             'role[openstack-ha]']
            #return role_list
        return []

    # README(shep): not executed on the server, skipping from code coverage
    def _expand_nodelist(self, nodelist, api):  # pragma: no cover
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

    # README(shep): not executed on the server, skipping from code coverage
    def _serialize_node_blob(self, blob):  # pragma: no cover
        result = {}
        for key, value in blob.items():
            if isinstance(value, chef.node.NodeAttributes):
                result[key] = self._serialize_node_blob(value)
            else:
                result[key] = value
        return result

    # README(shep): not executed on the server, skipping from code coverage
    def converge_chef(self, state_data, api,
                      node_id, **kwargs):  # pragma: no cover
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
        api.apply_expression(node_id, 'attrs.converged := false')

        if not 'chef_server_consumed' in node['facts']:
            return self._fail(msg='missing fact: chef_server_consumed')

        chef_server_consumed = node['facts']['chef_server_consumed']
        cs = api._model_get_by_id('nodes', chef_server_consumed)

        if not cs:
            return self._fail(msg='cannot find consumed chef server')

        if not verify_facts(cs, ['chef_server_uri',
                                 'chef_server_client_name',
                                 'chef_server_client_pem']):
            return self._faile(msg='chef server missing chef attrs')

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
        old_node_overrides = self._serialize_node_blob(chef_node.normal)

        self.logger.debug('Old node overrides: %s' % old_node_overrides)

        # we'll always converge node, just to be sure
        need_node_converge = False
        need_env_converge = False

        query = '"adventurator" in attrs.opencenter_agent_output_modules'
        adventurator = api._model_get_first_by_query('nodes', query)
        if not adventurator:
            self.logger.error('Could not find adventurator')
            return self._fail(msg='could not find adventurator')

        # we'll always stomp this stuff..

        # if old_node_overrides != node_attrs or \
        #         chef_node.chef_environment != chef_environment or\
        #         chef_node.run_list != self._map_roles(nova_role):
        self.logger.debug('Updating chef node')
        need_node_converge = True
        self.logger.debug('Setting environment to %s' % chef_environment)
        chef_node.chef_environment = chef_environment
        chef_node.normal = node_attrs
        old_runlist = chef_node.run_list
        chef_node.run_list = self._map_roles(nova_role)
        chef_node.save()

        if old_runlist != chef_node.run_list:
            # roles changed, refreshing env just in case searches are affected.
            need_env_converge = True

        if old_env_overrides != env_attrs:
            self.logger.debug('Updating environment')
            need_env_converge = True
            env.override_attributes = env_attrs
            env.save()

        nodelist = [node_id]

        if need_env_converge:
            # FIXME: this should be the top-level environment container...
            nodelist = self._expand_nodelist([node_id], api)
        elif need_node_converge:
            nodelist = [node_id]

        self.logger.debug('chef updating nodelist: %s' % nodelist)
        dsl = [{'primitive': 'run_chef', 'ns': {}}]
        # first run converge on the node in question
        api._model_create('tasks', {'action': 'adventurate',
                                    'node_id': adventurator['id'],
                                    'payload': {'nodes': [node_id],
                                                'adventure_dsl': dsl}})
        # now converge the affected nodes
        if node_id in nodelist:
            nodelist.remove(node_id)

        for conv_node in nodelist:
            api.apply_expression(conv_node, 'attrs.converged := false')

        if len(nodelist) > 0:
            api._model_create('tasks', {'action': 'adventurate',
                                        'node_id': adventurator['id'],
                                        'payload': {'nodes': nodelist,
                                                    'adventure_dsl': dsl}})

        # FIXME: should poll for result here
        return self._ok()

    # README(shep): not executed on the server, skipping from code coverage
    def add_backend(self, api, node_id, **kwargs):  # pragma: no cover
        return self._fail(msg='backend added by install_chef')
