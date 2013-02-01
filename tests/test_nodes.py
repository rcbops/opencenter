# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import random
import string
import unittest2

from roush.db.database import init_db
from roush import webapp

import util


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class NodeCreateTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='tests/test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.name = _randomStr(10)
        self.desc = _randomStr(30)
        self.attribs = {_randomStr(5): _randomStr(10),
                        _randomStr(5): {_randomStr(5): _randomStr(10)},
                        _randomStr(5): [_randomStr(10), _randomStr(10)]}
        self.content_type = 'application/json'
        # need to create a test cluster
        self.clus1_name = _randomStr(10)
        self.clus1_desc = _randomStr(30)
        self.clus1_data = {'name': self.clus1_name,
                           'description': self.clus1_desc}
        # neet to create a test role
        self.shep = 30

    @classmethod
    def tearDownClass(self):
        pass

    def _delete_node(self, node_id):
        # if self.foo.config['backend'] != 'null':
        #     time.sleep(2 * self.shep)  # chef-solr indexing can be slow
        resp = self.app.delete('/nodes/%s' % node_id,
                               content_type=self.content_type)
        self.assertEquals(resp.status_code, 200)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 200)
        self.assertEquals(out['message'], 'Node deleted')

    def test_create_node_with_name_only(self):
        data = {'name': self.name}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        out = json.loads(resp.data)
        self.foo.logger.debug(out)
        self.assertEquals(resp.status_code, 201)
        self.assertEquals(out['status'], 201)
        self.assertEquals(out['message'], 'Node Created')
        self.assertEquals(out['node']['name'], self.name)

        # Cleanup the node we created
        self._delete_node(out['node']['id'])

    def test_create_node_without_name(self):
        data = {'description': self.desc}
        resp = self.app.post('/nodes/',
                             content_type=self.content_type,
                             data=json.dumps(data))
        self.assertEquals(resp.status_code, 400)
        out = json.loads(resp.data)
        self.assertEquals(out['status'], 400)

    def _generic_test(self, method, path, code):
        resp = self.app.__getattribute__(method)(
            path,
            content_type=self.content_type)
        self.assertEquals(resp.status_code, code)


class NodeInvalidHTTPMethodTests(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.foo = webapp.Thing('roush', configfile='tests/test.conf', debug=True)
        init_db(self.foo.config['database_uri'])
        self.app = self.foo.test_client()
        self.content_type = 'application/json'

    @classmethod
    def tearDownClass(self):
        pass

    def _execute_method(self, method_name, path, http_code):
        """Helper function that will execute a method, against a path and
           verify the returned http code

        :param method_name: name of the http method to execute
        :param path: path to execute the http call against
        :param http_code: http error code to validate against
        """
        resp = self.app.__getattribute__(method_name)(
            path,
            content_type=self.content_type)
        self.assertEquals(resp.status_code, http_code)

    def test_405_returned_by_delete_on_nodes(self):
        self._execute_method('delete', '/nodes/', 405)

    def test_405_returned_by_patch_on_nodes(self):
        self._execute_method('patch', '/nodes/', 405)

    def test_405_returned_by_put_on_nodes(self):
        self._execute_method('put', '/nodes/', 405)

    def test_405_returned_by_post_on_nodes_with_id(self):
        self._execute_method('post', '/nodes/1', 405)

    def test_405_returned_by_patch_on_nodes_with_id(self):
        self._execute_method('patch', '/nodes/1', 405)


class NodeOtherTests(util.RoushTestCase):
    def setUp(self):
        self.cluster = self._model_create('nodes', name='cluster-1')
        self.node = self._model_create('nodes', name='node-1')
        self._model_create('facts', node_id=self.node['id'],
                           key='parent_id',
                           value=self.cluster['id'])

    def tearDown(self):
        self._model_delete('nodes', self.node['id'])
        self._model_delete('nodes', self.cluster['id'])

    def test_hierarchical_tree_view(self):
        resp = self._client_request('get', '/nodes/%s/tree' %
                                    self.cluster['id'])

        self.assertEquals(resp.status_code, 200)

        data = json.loads(resp.data)['children']

        self.assertEquals(data['id'], self.cluster['id'])
        self.assertEquals(len(data['children']), 1)
        self.assertEquals(data['children'][0]['id'], self.node['id'])

    def test_non_hierarchical_tree_view(self):
        resp = self._client_request('get', '/nodes/%s/tree' %
                                    self.node['id'])

        self.assertEquals(resp.status_code, 200)

        data = json.loads(resp.data)['children']

        self.assertEquals(data['id'], self.node['id'])
        self.assertTrue('children' not in data)

    def test_bad_tree_view(self):
        resp = self._client_request('get', '/nodes/99/tree')
        self.assertEquals(resp.status_code, 404)


    # FIXME: need loop detection in merge_upwards
    # def test_loop(self):
    #     # loop should be terminated before descending into the looped
    #     # item, so should look indistinguishable from the tree_view test.
    #     self._model_update('node', self.cluster['id'],
    #                        parent_id=self.node['id'])

    #     resp = self._client_request('get', '/nodes/%s/tree' %
    #                                 self.cluster['id'])

    #     self.assertEquals(resp.status_code, 200)

    #     data = json.loads(resp.data)['children']

    #     self.assertEquals(data['id'], self.cluster['id'])
    #     self.assertEquals(len(data['children']), 1)
    #     self.assertEquals(data['children'][0]['id'], self.node['id'])
