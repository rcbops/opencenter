#!/usr/bin/env python

import roush


class ContainerBackend(roush.backends.Backend):
    def __init__(self):
        super(ContainerBackend, self).__init__(__file__)

    def create_subcontainer(self, api, node_id, **kwargs):
        # creating subcontainers is kind of sketchy.  we'll
        # ignore the node_id, and create subcontainers from
        # the parent_id or name we get passed.  This is pretty
        # handwavey
        parent_id = None

        if not 'name' in kwargs:
            self.logger.error('no "name" argument in create_subcontainer')
            return False

        if 'parent_id' in kwargs:
            parent_id = int(kwargs['parent_id'])
        elif 'parent_name' in kwargs:
            query = 'name="%s"' % kwargs['parent_name']

            parent = api._model_query('nodes', query)
            if parent is None:
                self.logger.error('cannot find parent container named ' %
                                  kwargs['parent_name'])
                return False

            if len(parent) > 1:
                self.logger.error('multiple containers named ' %
                                  kwargs['parent_name'])
                return False

            parent_id = parent[0]['id']

        # now we have the parent_id, let's make the child container.
        new_container = api._model_create('nodes', {'name': kwargs['name']})
        new_id = new_container['id']

        # now, set up the proper facts.
        api._model_create('facts', {'node_id': new_id,
                                    'key': 'backends',
                                    'value': ['node', 'container']})
        api._model_create('facts', {'node_id': new_id,
                                    'key': 'parent_id',
                                    'value': parent_id})

        return True
