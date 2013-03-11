# vim: tabstop=4 shiftwidth=4 softtabstop=4
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
import imp
import tests
import unittest2
util_facts = imp.load_module('util_facts',
                             *imp.find_module('util', tests.__path__))
from opencenter.db import exceptions


def identity(x):
    return x


def to_list(x):
    return [x]


class UnorderedList(list):
    def __eq__(self, x):
        if isinstance(x, list):
            if len(x) != len(self):
                return False
            for element in x:
                if not element in self:
                    return False
            return True
        else:
            return super(UnorderedList, self).__eq__(x)


class FactsTests(util_facts.OpenCenterTestCase):
    base_object = 'fact'

    def setUp(self):
        self._clean_all()

        self.c2 = self._model_create('nodes',
                                     name=self._random_str())
        self.c1 = self._model_create('nodes',
                                     name=self._random_str())
        self._model_create('facts',
                           node_id=self.c1['id'],
                           key='parent_id',
                           value=self.c2['id'])
        self.n1 = self._model_create('nodes',
                                     name=self._random_str())
        self._model_create('facts',
                           node_id=self.n1['id'],
                           key='parent_id',
                           value=self.c1['id'])

    def tearDown(self):
        c2_facts = self._model_filter('facts',
                                      'node_id=%s' % self.c2['id'])

        c1_facts = self._model_filter('facts',
                                      'node_id=%s' % self.c1['id'])

        n1_facts = self._model_filter('facts',
                                      'node_id=%s' % self.n1['id'])

        for fact_id in [x['id'] for x in c2_facts + c1_facts + n1_facts]:
            self.app.logger.debug('deleting fact %s' % fact_id)
            self._model_delete('facts', fact_id)

        self._model_delete('nodes', self.n1['id'])
        self._model_delete('nodes', self.c2['id'])
        self._model_delete('nodes', self.c1['id'])

        all_facts = self._model_get_all('facts')
        all_nodes = self._model_get_all('nodes')

    def test_001_add_fact(self):
        self._model_create('facts', node_id=self.n1['id'],
                           key='node_data',
                           value='blah')

        n1_facts = self._model_get_by_id('nodes', self.n1['id'])['facts']

        self.assertEquals(n1_facts['node_data'], 'blah')

    def test_add_fact_non_existant_node_fails(self):
        self.assertRaises(exceptions.NodeNotFound, self._model_create, 'facts',
                          node_id=99999, key='bad_node', value='data')

    def inheritance_helper(self, fact, grand_parent,
                           parent, child_only,
                           skip_parent, skip_child,
                           f=identity):
        # setup grandparent -> parent -> node with conflicting facts
        f1 = self._model_create('facts', node_id=self.n1['id'],
                                key=fact,
                                value=f('n1'))
        f2 = self._model_create('facts', node_id=self.c1['id'],
                                key=fact,
                                value=f('c1'))
        f3 = self._model_create('facts', node_id=self.c2['id'],
                                key=fact,
                                value=f('c2'))

        #all attributes set, eldest should not be modified
        c2 = self._model_get_by_id('nodes', self.c2['id'])
        self.assertEquals(c2['facts'][fact], f('c2'))

        # test grandparent policy enforced
        n1 = self._model_get_by_id('nodes', self.n1['id'])
        self.assertEquals(n1['facts'][fact], grand_parent)
        self._model_delete('facts', f3['id'])

        # c1 is now the top parent, verify c1 fact is unchanged
        c1 = self._model_get_by_id('nodes', self.c1['id'])
        self.assertEquals(c1['facts'][fact], f('c1'))

        # test parent policy enforced
        n1 = self._model_get_by_id('nodes', self.n1['id'])
        self.assertEquals(n1['facts'][fact], parent)
        self._model_delete('facts', f2['id'])

        # test no parent behavior
        n1 = self._model_get_by_id('nodes', self.n1['id'])
        self.assertEquals(n1['facts'][fact], child_only)

        # test skipped parent (grandparent + node)
        f3 = self._model_create('facts', node_id=self.c2['id'],
                                key=fact,
                                value=f('c2'))
        n1 = self._model_get_by_id('nodes', self.n1['id'])
        self.assertEquals(n1['facts'][fact], skip_parent)
        self._model_delete('facts', f1['id'])

        # test grandparent + parent (no child node attribute)
        f2 = self._model_create('facts', node_id=self.c1['id'],
                                key=fact,
                                value=f('c1'))
        n1 = self._model_get_by_id('nodes', self.n1['id'])
        self.assertEquals(n1['facts'].get(fact, None), skip_child)
        self._model_delete('facts', f2['id'])
        self._model_delete('facts', f3['id'])

    def test_fact_inheritance_parent_clobber(self):
        # inheritance helper sets up a number of fact chains and checks
        # the results against the provided arguments.
        # each container/node contains f(node_name) as its value.
        # f is a kwarg that defaults to identity (lambda x: x)
        # c2 is a container that is the parent of c1.
        # c1 is a container that is the parent of n1
        # n1 is a terminal node.
        self.inheritance_helper("parent_clobbered",  # which fact to set
                                "c2",  # c2, c1, n1 set
                                "c1",  # c1, n1 set
                                "n1",  # n1 only set
                                "c2",  # c2, n1 set
                                "c2")  # c2, c1 set

    def test_fact_inheritance_child_clobber(self):
        # see test_fact_inheritance_parent_clobber for an example of
        # writing inheritance test.
        self.inheritance_helper("child_clobbered",
                                "n1", "n1", "n1", "n1", "c1")

    def test_fact_inheritance_default(self):
        # see test_fact_inheritance_parent_clobber for an example of
        # writing inheritance test.
        self.inheritance_helper("defaulted", "c2", "c1", "n1", "c2", "c2")

    def test_fact_inheritance_none(self):
        # see test_fact_inheritance_parent_clobber for an example of
        # writing inheritance test.
        self.inheritance_helper("noned", "n1", "n1", "n1", "n1", None)

    def test_fact_inheritance_union(self):
        # see test_fact_inheritance_parent_clobber for an example of
        # writing inheritance test.
        self.inheritance_helper("unioned",
                                UnorderedList(["c2", "c1", "n1"]),
                                UnorderedList(["c1", "n1"]),
                                UnorderedList(["n1"]),
                                UnorderedList(["c2", "n1"]),
                                UnorderedList(["c2", "c1"]),
                                f=to_list)

    def test_updating_facts(self):
        self._model_create('facts', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value')
        # now, do a create...
        self._model_create('facts', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value2')
        n1 = self._model_get_by_id('nodes', self.n1['id'])
        self.assertEquals(n1['facts']['test_fact'], 'test_value2')

    def test_list_all_facts(self):
        self._model_create('facts', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value')
        result = self._model_get_all('facts')
        # 2 facts are parent_ids from setup
        self.assertEquals(len(result), 3)

    def test_request_bad_fact(self):
        resp = self.client.get('/admin/facts/9999')
        self.assertEquals(resp.status_code, 404)

    def update_bad_fact(self):
        resp = self.client.put('/admin/facts/9999',
                               content_type='application/json',
                               data=json.dumps({'value': 'test'}))
        self.assertEquals(resp.status_code, 404)

    def test_request_fact(self):
        fact = self._model_create('facts', node_id=self.n1['id'],
                                  key='test_fact',
                                  value='test_value')
        self.app.logger.debug('fact: %s' % fact)
        self._model_get_by_id('facts', fact['id'])


def _modified_test_missing_create_field(self, missing_field, expected_code):
    bo = self.base_object
    bop = self._pluralize(bo)

    schema = self._model_get_schema(bo)
    all_fields = [x for x in schema]
    all_fields.remove('id')

    data = dict(zip(all_fields,
                    [self._valid_rand(schema[x]['type'])
                     for x in all_fields]))

    try:
        data['node_id'] = self.n1['id']
    except KeyError:
        pass

    data.pop(missing_field)

    # special case tasks -- need schema for enum type
    if bo == 'task' and 'state' in data:
        data['state'] = 'running'

    self.logger.debug('creating with data %s (missing %s)' %
                      (data, missing_field))

    util_facts._test_request_returns(self, 'post', '/admin/%s/' % bop, data,
                                     expected_code)
mod_test = _modified_test_missing_create_field

setattr(util_facts, '_test_missing_create_field', mod_test)

FactsTests = util_facts.inject(FactsTests)
