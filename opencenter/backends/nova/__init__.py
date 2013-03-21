#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

import opencenter
import string


class NovaBackend(opencenter.backends.Backend):
    def __init__(self):
        super(NovaBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        return []

    def _make_subcontainer(self, api, name, parent_id, facts, backends,
                           attrs=None):
        subcontainer = api._model_create('nodes', {'name': name})
        if subcontainer is None:
            return None
        if attrs is None:
            attrs = {}
        if facts is None:
            facts = {}

        facts.update({'parent_id': parent_id,
                      'backends': backends})
        data = {}
        data['facts'] = facts
        data['attrs'] = attrs
        for t in ['facts', 'attrs']:
            for k, v in data[t].items():
                d = {'key': k,
                     'value': v,
                     'node_id': subcontainer['id']}
                api._model_create(t, d)

        return subcontainer

    def create_az(self, state_data, api, node_id, **kwargs):
        if not 'az_name' in kwargs:
            return self._fail(msg='AZ Name is required')

        valid = string.letters + string.digits + "_"
        test_valid = all([c in valid for c in kwargs['az_name']])
        if not test_valid:
            return self._fail(msg='Name cannot contain spaces or special'
                                  'characters')
        r = api.nodes_query('(facts.parent_id = %s) and '
                            '(facts.nova_az = "%s")' % (
                                node_id, kwargs['az_name']))
        if len(r) > 0:
            return self._fail(msg='AZ Name should be unique within a cluster.')
        self._make_subcontainer(api,
                                'AZ %s' % kwargs['az_name'],
                                node_id,
                                {'nova_az': kwargs['az_name'],
                                 'libvirt_type': kwargs['libvirt_type']},
                                ['node', 'container', 'nova'])

        return self._ok()

    # README(shep): part of happy path, not excluding from code coverage
    def create_cluster(self, state_data, api, node_id, **kwargs):
        kwargs['nova_az'] = 'nova'

        # make sure we have good inputs
        if not 'cluster_name' in kwargs:
            return self._fail(msg='Cluster Name (cluster_name) required')
        valid = string.letters + string.digits + "_-"
        test_valid = all([c in valid for c in kwargs['cluster_name']])
        if not test_valid:
            return self._fail(msg='Cluster name must be entirely composed of'
                              ' alphanumeric characters, -s, or _s')
        r = api.nodes_query('facts.chef_environment = "%s"' % (
            kwargs['cluster_name'],))
        if len(r) > 0:
            return self._fail(msg='Cluster Name should be unique')

        cluster_facts = ["nova_public_if",
                         "keystone_admin_pw",
                         "nova_dmz_cidr",
                         "nova_vm_fixed_range",
                         "nova_vm_fixed_if",
                         "nova_vm_bridge",
                         "osops_mgmt",
                         "osops_nova",
                         "osops_public",
                         "libvirt_type"]

        environment_hash = {}
        for k, v in kwargs.items():
            if k in cluster_facts:
                environment_hash[k] = v

        environment_hash['chef_server_consumed'] = kwargs['chef_server']
        environment_hash['chef_environment'] = kwargs['cluster_name']
        environment_hash['ram_allocation_ratio'] = 1
        environment_hash['cpu_allocation_ratio'] = 16
        environment_hash['nova_use_single_default_gateway'] = "false"
        environment_hash['nova_network_dhcp_name'] = 'novalocal'

        # have the attribute map, let's make it an apply the
        # facts.
        cluster = self._make_subcontainer(
            api, kwargs['cluster_name'], node_id, environment_hash,
            ['node', 'container', 'nova', 'chef-environment'],
            attrs={"locked": True})

        if cluster is None:
            return self._fail(msg='cannot create nova cluster container')

        infra = self._make_subcontainer(
            api, 'Infrastructure', cluster['id'],
            {'nova_role': 'nova-controller-master', 'ha_infra': False},
            ['node', 'container', 'nova', 'nova-controller'])

        if infra is None:
            return self._fail(msg='cannot create "Infra" container')

        comp = self._make_subcontainer(
            api, 'Compute', cluster['id'],
            {'nova_role': 'nova-compute'},
            ['node', 'container', 'nova', 'nova-compute'],
            {"locked": True})

        if comp is None:
            return self._fail(msg='cannot create "Compute" container')

        az = kwargs['nova_az']

        self._make_subcontainer(
            api, 'AZ %s' % az, comp['id'], {'nova_az': az},
            ['node', 'container', 'nova'])

        return self._ok()
