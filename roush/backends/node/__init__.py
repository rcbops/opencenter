#!/usr/bin/env python

from roush import backends


class NodeBackend(backends.Backend):
    def __init__(self):
        super(NodeBackend, self).__init__(__file__)

    def additional_constraints(self, action, ns):
        if action == 'set_fact':
            if not 'key' in ns:
                raise ValueError('no key in ns')
            key = ns['key']

            # see what backend this key is in...
            for name, obj in backends.backend_objects.iteritems():
                if key in obj.facts:
                    return ['"%s" in facts.backends' % name]

            return ['1=2']

        return []

    def set_parent(self, api, node_id, parent):
        api._model_update_by_id('nodes', node_id,
                                {'parent_id': parent})
        return True

    def set_fact(self, api, node_id, key, value):
        # if the fact exists, update it, else create it.
        oldkeys = api._model_query('facts', 'node_id=%s and key=%s' %
                                   (node_id, key))

        if len(oldkeys) > 0:
            # update
            api._model_update_by_id('facts', {'id': oldkeys[0]['id'],
                                              'value': value})
        else:
            api._model_create('facts', {'node_id': node_id,
                                        'key': key,
                                        'value': value})

        return True
