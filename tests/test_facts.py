# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest2

from util import RoushTestCase
from util import inject


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


class FactsTests(RoushTestCase):
    base_object = 'fact'

    def setUp(self):
        self._clean_all()

        self.c2 = self._model_create('node',
                                     name=self._random_str())
        self.c1 = self._model_create('node',
                                     name=self._random_str())
        self._model_create('fact',
                           node_id=self.c1['id'],
                           key='parent_id',
                           value=self.c2['id'])
        self.n1 = self._model_create('node',
                                     name=self._random_str())
        self._model_create('fact',
                           node_id=self.n1['id'],
                           key='parent_id',
                           value=self.c1['id'])

    def tearDown(self):
        c2_facts = self._model_filter('fact',
                                      'node_id=%s' % self.c2['id'])

        c1_facts = self._model_filter('fact',
                                      'node_id=%s' % self.c1['id'])

        n1_facts = self._model_filter('fact',
                                      'node_id=%s' % self.n1['id'])

        for fact_id in [x['id'] for x in c2_facts + c1_facts + n1_facts]:
            self.app.logger.debug('deleting fact %s' % fact_id)
            self._model_delete('fact', fact_id)

        self._model_delete('node', self.n1['id'])
        self._model_delete('node', self.c2['id'])
        self._model_delete('node', self.c1['id'])

        all_facts = self._model_get_all('fact')
        all_nodes = self._model_get_all('node')

    def test_001_add_fact(self):
        self._model_create('fact', node_id=self.n1['id'],
                           key='node_data',
                           value='blah')

        n1_facts = self._model_get_by_id('node', self.n1['id'])['facts']

        self.assertEquals(n1_facts['node_data'], 'blah')

    def inheritance_helper(self, fact, grand_parent,
                           parent, child_only,
                           skip_parent, skip_child,
                           f=identity):
        # setup grandparent -> parent -> node with conflicting facts
        f1 = self._model_create('fact', node_id=self.n1['id'],
                                key=fact,
                                value=f('n1'))
        f2 = self._model_create('fact', node_id=self.c1['id'],
                                key=fact,
                                value=f('c1'))
        f3 = self._model_create('fact', node_id=self.c2['id'],
                                key=fact,
                                value=f('c2'))

        #all attributes set, eldest should not be modified
        c2 = self._model_get_by_id('node', self.c2['id'])
        self.assertEquals(c2['facts'][fact], f('c2'))

        # test grandparent policy enforced
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts'][fact], grand_parent)
        self._model_delete('fact', f3['id'])

        # c1 is now the top parent, verify c1 fact is unchanged
        c1 = self._model_get_by_id('node', self.c1['id'])
        self.assertEquals(c1['facts'][fact], f('c1'))

        # test parent policy enforced
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts'][fact], parent)
        self._model_delete('fact', f2['id'])

        # test no parent behavior
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts'][fact], child_only)

        # test skipped parent (grandparent + node)
        f3 = self._model_create('fact', node_id=self.c2['id'],
                                key=fact,
                                value=f('c2'))
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts'][fact], skip_parent)
        self._model_delete('fact', f1['id'])

        # test grandparent + parent (no child node attribute)
        f2 = self._model_create('fact', node_id=self.c1['id'],
                                key=fact,
                                value=f('c1'))
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts'].get(fact, None), skip_child)
        self._model_delete('fact', f2['id'])
        self._model_delete('fact', f3['id'])

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
        self._model_create('fact', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value')
        # now, do a create...
        self._model_create('fact', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value2')
        n1 = self._model_get_by_id('node', self.n1['id'])
        self.assertEquals(n1['facts']['test_fact'], 'test_value2')

    def test_list_all_facts(self):
        self._model_create('fact', node_id=self.n1['id'],
                           key='test_fact',
                           value='test_value')
        result = self._model_get_all('fact')
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
        fact = self._model_create('fact', node_id=self.n1['id'],
                                  key='test_fact',
                                  value='test_value')
        self.app.logger.debug('fact: %s' % fact)
        self._model_get_by_id('fact', fact['id'])


FactsTests = inject(FactsTests)
