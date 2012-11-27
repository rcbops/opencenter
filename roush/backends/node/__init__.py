#!/usr/bin/env python

from roush import backends


class NodeBackend(backends.Backend):
    def __init__(self):
        super(NodeBackend, self).__init__(__file__)

    # def set_fact(self, api, node_id, key, value):
    #     # if the fact exists, update it, else create it.
    #     oldkeys = api._model_query('facts', 'node_id=%s and key=%s' %
    #                                (node_id, key))

    #     if len(oldkeys) > 0:
    #         # update
    #         api._model_update_by_id('facts', {'id': oldkeys[0]['id'],
    #                                           'value': value})
    #     else:
    #         api._model_create('facts', {'node_id': node_id,
    #                                     'key': key,
    #                                     'value': value})

    #     return True
