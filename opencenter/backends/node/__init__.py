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

from opencenter import backends
import opencenter.webapp.ast
import opencenter.db.api


class NodeBackend(backends.Backend):
    def __init__(self):
        super(NodeBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        if action == 'set_fact':
            addl_constraints = []

            if not 'key' in ns:
                raise ValueError('no key in ns')
            key = ns['key']

            # see what backend this key is in...
            for name, obj in backends.backend_objects.iteritems():
                if key in obj.facts:
                    # we can only solve for settable facts.  If the
                    # fact is not settable, then there is likely (HAS TO BE!)
                    # a primitive to set this somewhere else.  Probably in
                    # the same backend.
                    fact_info = obj.facts[key]
                    if fact_info['settable'] is not True:
                        return None

                    addl_constraints.append('"%s" in facts.backends' % name)
                    # if fact_info['converge']:
                    #     addl_constraints.append('facts.converged = true')
                    return addl_constraints
            return None

        if action == 'unapply_fact':
            if not 'key' in ns:
                raise ValueError('no key in ns')

            key = ns['key']

            addl_constraints = []

            for name, obj in backends.backend_objects.iteritems():
                if key in obj.facts:
                    # we can only solve for settable facts.  If the
                    # fact is not settable, then there is likely (HAS TO BE!)
                    # a primitive to set this somewhere else.  Probably in
                    # the same backend.
                    addl_constraints.append('"%s" in facts.backends' % name)
                    fact_info = obj.facts[key]
                    if fact_info['converge'] is True:
                        addl_constraints.append('facts.converged = true')

                    return addl_constraints
            return None

        if action == 'apply_fact':
            if not 'key' in ns:
                raise ValueError('no key in ns')
            key = ns['key']

            addl_constraints = []
            # see what backend this key is in...
            for name, obj in backends.backend_objects.iteritems():
                if key in obj.facts:
                    # we can only solve for settable facts.  If the
                    # fact is not settable, then there is likely (HAS TO BE!)
                    # a primitive to set this somewhere else.  Probably in
                    # the same backend.
                    addl_constraints.append('"%s" in facts.backends' % name)
                    fact_info = obj.facts[key]
                    if fact_info['converge'] is True:
                        addl_constraints.append('facts.converged = true')

                    return addl_constraints
            return None

        if action == 'add_backend':
            if ns['backend'] == 'node':
                return []

            if opencenter.backends.primitive_by_name(
                    '%s.add_backend' % ns['backend']) is None:
                return []
            else:
                return None

        if action == 'set_parent':
            new_constraints = []

            if not 'parent' in ns:
                raise ValueError('no parent set')
            parent = api._model_get_by_id('nodes', ns['parent'])
            if 'container' in parent['facts'].get('backends', {}):
                # should already be the case, but...
                new_constraints.append('"node" in facts.backends')

                existing_node = api._model_get_by_id('nodes', node_id)
                if existing_node.get('attrs', {}).get('locked', False):
                    # Node is locked, set_parent not allowed.
                    return None
                if parent.get('attrs', {}).get('locked', False):
                    # parent is locked
                    return None

                ephemeral_api = opencenter.db.api.ephemeral_api_from_api(api)
                opencenter.webapp.ast.apply_expression(existing_node,
                                                       'facts.parent_id :='
                                                       '"%s"' %
                                                       parent['id'],
                                                       ephemeral_api)

                proposed_node = ephemeral_api._model_get_by_id('nodes',
                                                               node_id)

                self.logger.debug('Setting parent would change %s to %s' %
                                  (existing_node, proposed_node))

                # this should be much smarter.  losing vs gaining,
                # and add/remove facts as appropriate.
                all_keys = set(existing_node['facts'].keys() +
                               proposed_node['facts'].keys())
                changed_facts = []

                for key in all_keys:
                    if existing_node['facts'].get(key, None) != \
                            proposed_node['facts'].get(key, None):
                        changed_facts.append(key)

                self.logger.debug('Changed facts: %s' % changed_facts)

                required_facts = []
                for key in changed_facts:
                    action = 'unapply_fact'
                    value = None

                    if key in proposed_node['facts']:
                        action = 'unapply_fact'
                        value = proposed_node['facts'][key]

                    # run this through the fact discovery
                    new_fact_reqs = self.additional_constraints(
                        api, node_id, action, {'key': key,
                                               'value': value})

                    if new_fact_reqs is None:
                        self.logger.debug('Impossible to satisfy %s->%s' %
                                          (key, value))
                        return None

                    for fact in new_fact_reqs:
                        if not fact in new_constraints:
                            new_constraints.append(fact)

                self.logger.debug('Required facts: %s' % required_facts)
                return new_constraints

                # parent_facts = api._model_get_by_id('nodes', parent)

                # determine what facts are going to be inherited,
                # so we can run the 'set_fact' (apply fact?)
                # node differ?
                # inherited_facts = parent['facts'].get('inherited', {})
                # return ['facts.%s="%s"' % (k, v)
                #         for k, v in inherited_facts.items()]
            else:
                # cannot set_parent to something that isn't a container
                return None
        return []

    def set_parent(self, state_data, api, node_id, **kwargs):
        reply_data = {}

        current = api._model_get_first_by_query(
            'facts', 'node_id = %s and key="parent_id"' % node_id)

        # it's possible we have unparented things
        current_parent = 1
        if current:
            current_parent = current['value']

        if current:
            reply_data['rollback'] = {'primitive': 'node.set_parent',
                                      'ns': {'parent': current_parent}}

        parent = kwargs['parent']
        opencenter.webapp.ast.apply_expression(node_id,
                                               'facts.parent_id := %s'
                                               % parent,
                                               api)

        return self._ok(data=reply_data)

    def apply_fact(self, state_data, api, node_id, **kwargs):
        node = api.node_get_by_id(node_id)
        key, value = kwargs['key'], kwargs['value']
        curval = node['facts'].get(key, None)
        if key == "chef_environment" and (curval is not None
                                          or curval != value):
            return self._fail()
        self.logger.debug("Applying (vs. setting) fact %s->%s" %
                          (key, value))

        # something should be done here.
        return self._ok()

    def del_fact(self, state_data, api, node_id, **kwargs):
        """
        delete an existing fact.

        required kwargs:
        key: key of fact to delete
        """

        if not 'key' in kwargs:
            return self._fail(msg='need "key" kwarg')

        old_fact = None

        old_fact = api._model_query(
            'facts', 'node_id=%d and key="%s"' % (int(node_id),
                                                  kwargs['key']))

        if old_fact is None:
            return self._ok()  # no rollback necessary

        api._model_delete_by_id('facts', old_fact[0]['id'])

        reply_data = {
            'rollback': {
                'primitive': 'node.set_fact',
                'ns': {
                    'key': old_fact['key'],
                    'value': old_fact['value']}}}

        return self._ok(data=reply_data)

    def set_fact(self, state_data, api, node_id, **kwargs):
        reply_data = {}

        key, value = kwargs['key'], kwargs['value']

        # if the fact exists, update it, else create it.
        oldkeys = api._model_query('facts', 'node_id=%s and key=%s' %
                                   (node_id, key))

        _by_key = dict([[x['key'], x['value']] for x in oldkeys])

        if key in _by_key and _by_key[key] == value:
            # we dont' need to set the value, merely apply it -- no rollback
            return self.apply_fact(state_data, api, node_id, **kwargs)
        elif key in _by_key:
            reply_data['rollback'] = {'primitive': 'node.set_fact',
                                      'ns': {'key': key,
                                             'value': _by_key[key]}}
        else:  # key not in _by_key
            reply_data['rollback'] = {'primitive': 'node.del_fact',
                                      'ns': {'key': key}}

        if len(oldkeys) > 0:
            # update
            api._model_update_by_id('facts', {'id': oldkeys[0]['id'],
                                              'value': value})
        else:
            api._model_create('facts', {'node_id': node_id,
                                        'key': key,
                                        'value': value})

        return self._ok(data=reply_data)

    def del_attr(self, state_data, api, node_id, **kwargs):
        """
        delete an existing node attribute

        required kwargs:
        key: key of attr to delete
        """

        if not 'key' in kwargs:
            return self._fail(msg='need either "key" kwarg')

        old_attr = None

        old_attr = api._model_query(
            'attrs', 'node_id=%d and key="%s"' % (int(node_id),
                                                  kwargs['key']))

        if old_attr is None:
            return self._ok()

        api._model_delete_by_id('attrs', old_attr[0]['id'])

        reply_data = {
            'rollback': {
                'primitive': 'node.set_attr',
                'ns': {
                    'key': old_attr['key'],
                    'value': old_attr['value']}}}

        return self._ok(data=reply_data)

    def set_attr(self, state_data, api, node_id, **kwargs):
        reply_data = {}
        key, value = kwargs['key'], kwargs['value']
        oldkeys = api._model_query('facts', 'node_id=%s and key=%s' %
                                   (node_id, key))
        _by_key = dict([[x['key'], x['value']] for x in oldkeys])
        if key in _by_key:
            reply_data['rollback'] = {'primitive': 'node.set_attr',
                                      'ns': {'key': key,
                                             'value': _by_key[key]}}
        else:
            reply_data['rollback'] = {'primitive': 'node.del_attr',
                                      'ns': {'key': key}}

        api._model_create('attrs', {"node_id": node_id,
                                    'key': key,
                                    'value': value})

        return self._ok(data=reply_data)

    def add_backend(self, state_data, api, node_id, **kwargs):
        reply_data = {}

        self.logger.debug('adding backend %s', kwargs['backend'])

        old_node = api._model_get_by_id('nodes', node_id)
        old_backend = old_node['facts'].get('backends', [])

        reply_data['rollback'] = {'primitive': 'node.set_fact',
                                  'ns': {'key': 'backends',
                                         'value': old_backend}}

        opencenter.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "%s")' %
            kwargs['backend'], api)

        return self._ok(data=reply_data)
