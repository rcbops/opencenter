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
import opencenter.backends
# import opencenter.db.api


class NovaControllerBackend(opencenter.backends.Backend):
    def __init__(self):
        super(NovaControllerBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        if action == "add_backend":
            node = api.node_get_by_id(node_id)
            parent_id = node['facts']['parent_id']
            count = len(api.nodes_query(
                'facts.parent_id = %s or facts.parent_id = "%s"' % (
                    parent_id, parent_id)))
            if count > 1:
                return ['facts.ha_infra = true']
            else:
                return []
        else:
            return []

    # README(shep): not executed on the server, skipping from code coverage
    def _parent_list(self, api, starting_node):  # pragma: no cover
        ret = list()
        node = starting_node
        while 'parent_id' in node['facts']:
            ret.append(node['facts']['parent_id'])
            node = api.node_get_by_id(node['facts']['parent_id'])
        return ret

    # README(shep): not executed on the server, skipping from code coverage
    def _find_chef_environment_node(self, api, node):  # pragma: no cover
        # need to build a list of parent_ids
        parent_list = self._parent_list(api, node)
        self.logger.debug('*** PARENT_LIST: %s' % parent_list)
        # revers the list inplace
        parent_list.reverse()
        self.logger.debug('*** REVERSE_PARENT_LIST: %s' % parent_list)
        ret = None
        for p_id in parent_list:
            parent_node = api.node_get_by_id(p_id)
            self.logger.debug('****** INSPECTING NODE: %s' % parent_node)
            if 'backends' in parent_node['facts']:
                if 'chef-environment' in parent_node['facts']['backends']:
                    ret = parent_node
                    break
        self.logger.debug('*** RETURNING NODE: %s' % ret)
        return ret

    # README(shep): not executed on the server, skipping from code coverage
    def add_backend(self, state_data, api,
                    node_id, **kwargs):  # pragma: no cover
        api.apply_expression(node_id,
                             'attrs.locked := true')
        return opencenter.backends.primitive_by_name('node.add_backend')(
            state_data, api, node_id, backend='nova-controller')

    # README(shep): not executed on the server, skipping from code coverage
    def make_infra_ha(self, state_data, api,
                      node_id, **kwargs):  # pragma: no cover
        self.logger.debug('*** INIT KWARGS: %s' % kwargs)
        self.logger.debug('*** INIT STATE_DATA: %s' % state_data)
        if 'nova_api_vip' not in kwargs:
            return self._fail(msg='Nova API VIP (nova_api_vip) required')

        if 'nova_mysql_vip' not in kwargs:
            return self._fail(msg='Nova MySQL VIP (nova_mysql_vip) required')

        if 'nova_rabbitmq_vip' not in kwargs:
            return self._fail(
                msg='Nova RabbitMQ VIP (nova_rabbitmq_vip) required')

        api.apply_expression(
            node_id,
            'facts.nova_role := "%s"' % 'nova-controller-backup')

        node = api.node_get_by_id(node_id)
        api.apply_expression(node['facts']['parent_id'],
                             'facts.ha_infra := true')
        api.apply_expression(node['facts']['parent_id'],
                             'attrs.locked := true')
        # Need to find my environment
        chef_env_node = self._find_chef_environment_node(api, node)
        if chef_env_node is not None:
            self.logger.debug('MY CHEF NODE: %s' % chef_env_node)
            vips = ['nova_api_vip', 'nova_rabbitmq_vip', 'nova_mysql_vip']
            for vip in vips:
                api.apply_expression(
                    chef_env_node['id'],
                    'facts.%s := "%s"' % (vip, kwargs[vip]))
            return self._ok()
        else:
            return self._fail(msg='Unable to determine Chef Environment Node')
