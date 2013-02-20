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

import roush


class NovaBackend(roush.backends.Backend):
    def __init__(self):
        super(NovaBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        return []

    def _make_subcontainer(self, api, name, parent_id, facts, backends):
        subcontainer = api._model_create('nodes', {'name': name})
        if subcontainer is None:
            return None

        facts.update({'parent_id': parent_id,
                      'backends': backends})

        for k, v in facts.items():
            data = {'key': k,
                    'value': v,
                    'node_id': subcontainer['id']}

            api._model_create('facts', data)

        return subcontainer

    def create_az(self, state_data, api, node_id, **kwargs):
        if not 'az_name' in kwargs:
            return self._fail(msg='AZ Name is required')

        self._make_subcontainer(api,
                                'AZ %s' % kwargs['az_name'],
                                node_id,
                                {'nova_az': kwargs['az_name']},
                                ['node', 'container', 'nova'])

        return self._ok()

    def create_cluster(self, state_data, api, node_id, **kwargs):
        if not 'cluster_name' in kwargs:
            return self._fail(msg='Cluster Name (cluster_name) required')

        cluster_facts = ["nova_public_if",
                         "keystone_admin_pw",
                         "nova_dmz_cidr",
                         "nova_vm_fixed_range",
                         "nova_vm_fixed_if",
                         "nova_vm_bridge",
                         "osops_mgmt",
                         "osops_nova",
                         "osops_public"]

        environment_hash = {}
        for k, v in kwargs.items():
            if k in cluster_facts:
                environment_hash[k] = v

        environment_hash['chef_server_consumed'] = kwargs['chef_server']
        environment_hash['chef_environment'] = kwargs['cluster_name']

        # have the attribute map, let's make it an apply the
        # facts.
        cluster = self._make_subcontainer(
            api, kwargs['cluster_name'], node_id, environment_hash,
            ['node', 'container', 'nova', 'chef-environment'])

        if cluster is None:
            return self._fail(msg='cannot create nova cluster container')

        infra = self._make_subcontainer(
            api, 'Infrastructure', cluster['id'],
            {'nova_ha_enabled': 'true'},
            ['node', 'container', 'nova', 'nova-ha'])

        if infra is None:
            return self._fail(msg='cannot create "Infra" container')

        comp = self._make_subcontainer(
            api, 'Compute', cluster['id'],
            {'nova_role': 'nova-compute'}, ['node', 'container', 'nova',
                                            'nova-compute'])

        if comp is None:
            return self._fail(msg='cannot create "Compute" container')

        az = 'nova'
        if 'nova_az' in kwargs:
            az = kwargs['nova_az']

        self._make_subcontainer(
            api, 'AZ %s' % az, comp['id'], {'nova_az': az},
            ['node', 'container', 'nova'])

        return self._ok()
