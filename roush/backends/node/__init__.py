#!/usr/bin/env python

from roush import backends
import roush.webapp.ast
import roush.db.api


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

            if roush.backends.primitive_by_name(
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

                ephemeral_api = roush.db.api.ephemeral_api_from_api(api)
                roush.webapp.ast.apply_expression(existing_node,
                                                  'facts.parent_id := "%s"' %
                                                  parent['id'], ephemeral_api)
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
                    if not key in proposed_node['facts']:
                        # we'll assume deleting a constraint doesn't
                        # actually increase your constraints
                        # new_constraints.append('facts.%s := None' % key)
                        pass
                    else:
                        # FIXME: needs to be type aware
                        value = proposed_node['facts'][key]

                        # run this through the fact discovery
                        new_fact_reqs = self.additional_constraints(
                            api, node_id, 'apply_fact', {'key': key,
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

    def set_parent(self, api, node_id, **kwargs):
        parent = kwargs['parent']
        roush.webapp.ast.apply_expression(node_id,
                                          'facts.parent_id := %s' % parent,
                                          api)

        return True

    def apply_fact(self, api, node_id, **kwargs):
        key, value = kwargs['key'], kwargs['value']

        self.logger.debug("Applying (vs. setting) fact %s->%s" %
                          (key, value))

        # something should be done here.
        return True

    def set_fact(self, api, node_id, **kwargs):
        key, value = kwargs['key'], kwargs['value']

        # if the fact exists, update it, else create it.
        oldkeys = api._model_query('facts', 'node_id=%s and key=%s' %
                                   (node_id, key))

        _by_key = dict([[x['key'], x['value']] for x in oldkeys])

        if key in _by_key and _by_key[key] == value:
            # we dont' need to set the value, merely apply it
            return self.apply_fact(api, node_id, **kwargs)

        if len(oldkeys) > 0:
            # update
            api._model_update_by_id('facts', {'id': oldkeys[0]['id'],
                                              'value': value})
        else:
            api._model_create('facts', {'node_id': node_id,
                                        'key': key,
                                        'value': value})

        return True

    def add_backend(self, api, node_id, **kwargs):
        self.logger.debug('adding backend %s', kwargs['backend'])

        roush.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "%s")' %
            kwargs['backend'], api)

        return True
