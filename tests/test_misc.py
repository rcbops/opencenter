# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest2

import roush.webapp.utility

from util import RoushTestCase


class MiscTests(RoushTestCase):
    def __init__(self, *args, **kwargs):
        super(MiscTests, self).__init__(*args, **kwargs)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_node_expansion(self):
        container1 = self._model_create('node', name='container1')
        container2 = self._model_create('node', name='container2')
        self._model_create('fact', node_id=container1['id'],
                           key='parent_id',
                           value=container2['id'])
        node1 = self._model_create('node', name='node1')
        self._model_create('fact', node_id=node1['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('fact', node_id=container1['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('fact', node_id=container2['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('fact', node_id=node1['id'],
                           key='backends', value=['node'])

        nodelist = roush.webapp.utility.expand_nodelist([container1['id']])

        self.logger.debug('Expanded nodelist: %s' % nodelist)

        self.assertEquals(len(nodelist), 1)
        self.assertEquals(nodelist[0], node1['id'])

        self._clean_table('node')
        self._clean_table('fact')
