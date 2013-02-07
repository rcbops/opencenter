# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
        container1 = self._model_create('nodes', name='container1')
        container2a = self._model_create('nodes', name='container2a')
        container2b = self._model_create('nodes', name='container2b')
        container3a = self._model_create('nodes', name='container3a')
        self._model_create('facts', node_id=container2a['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=container2b['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=container3a['id'],
                           key='parent_id',
                           value=container2a['id'])
        self._model_create('facts', node_id=container1['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container2a['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container2b['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container3a['id'],
                           key='backends', value=['container', 'node'])
        node1 = self._model_create('nodes', name='node1')
        node2a = self._model_create('nodes', name='node2a')
        node2b = self._model_create('nodes', name='node2b')
        node3a = self._model_create('nodes', name='node3a')
        self._model_create('facts', node_id=node1['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=node1['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node2a['id'],
                           key='parent_id',
                           value=container2a['id'])
        self._model_create('facts', node_id=node2a['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node2b['id'],
                           key='parent_id',
                           value=container2b['id'])
        self._model_create('facts', node_id=node2b['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node3a['id'],
                           key='parent_id',
                           value=container3a['id'])
        self._model_create('facts', node_id=node3a['id'],
                           key='backends', value=['node'])

        nodelist = roush.webapp.utility.expand_nodelist([container1['id']])

        self.logger.debug('Expanded nodelist: %s' % nodelist)
        #node list should contain ids of node1, node2a, node2b, and node3a
        self.assertEquals(len(nodelist), 4)
        self.assertTrue(node1['id'] in nodelist)

        self._clean_table('nodes')
        self._clean_table('facts')

    def test_get_direct_children(self):
        container1 = self._model_create('nodes', name='container1')
        container2a = self._model_create('nodes', name='container2a')
        container2b = self._model_create('nodes', name='container2b')
        container3a = self._model_create('nodes', name='container3a')
        self._model_create('facts', node_id=container2a['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=container2b['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=container3a['id'],
                           key='parent_id',
                           value=container2a['id'])
        self._model_create('facts', node_id=container1['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container2a['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container2b['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container3a['id'],
                           key='backends', value=['container', 'node'])
        node1 = self._model_create('nodes', name='node1')
        node2a = self._model_create('nodes', name='node2a')
        node2b = self._model_create('nodes', name='node2b')
        node3a = self._model_create('nodes', name='node3a')
        self._model_create('facts', node_id=node1['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=node1['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node2a['id'],
                           key='parent_id',
                           value=container2a['id'])
        self._model_create('facts', node_id=node2a['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node2b['id'],
                           key='parent_id',
                           value=container2b['id'])
        self._model_create('facts', node_id=node2b['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node3a['id'],
                           key='parent_id',
                           value=container3a['id'])
        self._model_create('facts', node_id=node3a['id'],
                           key='backends', value=['node'])

        nodelist = roush.webapp.utility.get_direct_children(container1['id'])

        self.logger.debug('Expanded nodelist: %s' % nodelist)
        #nodelist should contain full records for node1, container2a, and
        #container2b
        node_ids = [n['id'] for n in nodelist]
        self.assertEquals(len(nodelist), 3)
        self.assertTrue(node1['id'] in node_ids
                        and container2a['id'] in node_ids
                        and container2b['id'] in node_ids)

        self._clean_table('nodes')
        self._clean_table('facts')

    def test_full_node_expansion(self):
        container1 = self._model_create('nodes', name='container1')
        container2a = self._model_create('nodes', name='container2a')
        container2b = self._model_create('nodes', name='container2b')
        container3a = self._model_create('nodes', name='container3a')
        self._model_create('facts', node_id=container2a['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=container2b['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=container3a['id'],
                           key='parent_id',
                           value=container2a['id'])
        self._model_create('facts', node_id=container1['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container2a['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container2b['id'],
                           key='backends', value=['container', 'node'])
        self._model_create('facts', node_id=container3a['id'],
                           key='backends', value=['container', 'node'])
        node1 = self._model_create('nodes', name='node1')
        node2a = self._model_create('nodes', name='node2a')
        node2b = self._model_create('nodes', name='node2b')
        node3a = self._model_create('nodes', name='node3a')
        self._model_create('facts', node_id=node1['id'],
                           key='parent_id',
                           value=container1['id'])
        self._model_create('facts', node_id=node1['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node2a['id'],
                           key='parent_id',
                           value=container2a['id'])
        self._model_create('facts', node_id=node2a['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node2b['id'],
                           key='parent_id',
                           value=container2b['id'])
        self._model_create('facts', node_id=node2b['id'],
                           key='backends', value=['node'])
        self._model_create('facts', node_id=node3a['id'],
                           key='parent_id',
                           value=container3a['id'])
        self._model_create('facts', node_id=node3a['id'],
                           key='backends', value=['node'])

        nodelist = roush.webapp.utility.fully_expand_nodelist(
            [container1['id']])

        self.logger.debug('Expanded nodelist: %s' % nodelist)
        #node list should contain ids of container1, container2a,
        #container2b, container3a, node1, node2a, node2b, and node3a
        self.assertEquals(len(nodelist), 8)
        self.assertTrue(node1['id'] in nodelist
                        and container3a['id'] in nodelist
                        and container1['id'] in nodelist)

        self._clean_table('nodes')
        self._clean_table('facts')

    def test_unprovisioned_container(self):
        n = roush.webapp.utility.unprovisioned_container()
        self.assertTrue(n is not None)
        n2 = roush.webapp.utility.unprovisioned_container()
        self.assertTrue(n['id'] == n2['id'])
        self._clean_table('nodes')
        self._clean_table('facts')
