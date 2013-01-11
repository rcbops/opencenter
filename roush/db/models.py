import copy
import json
import time

from sqlalchemy import Column, Integer, String, ForeignKey, Enum, event
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
import sqlalchemy.types as types
from sqlalchemy.exc import InvalidRequestError

from database import Base
import api as db_api
import inmemory
import roush.backends

roush.backends.load()


# Special Fields
class JsonBlob(types.TypeDecorator):
    impl = types.Text

    def _is_valid_obj(self, value):
        if isinstance(value, dict) or isinstance(value, list):
            return True
        else:
            return False

    def process_bind_param(self, value, dialect):
        if self._is_valid_obj(value):
            return json.dumps(value)
        else:
            raise InvalidRequestError("%s is not an accepted type" %
                                      type(value))

    def process_result_value(self, value, dialect):
        if value is None:
            value = '{}'
        return json.loads(value)


class JsonEntry(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            value = ''
        return json.loads(value)


class JsonRenderer(object):
    def __new__(cls, *args, **kwargs):
        obj = super(JsonRenderer, cls).__new__(cls, *args, **kwargs)
        obj.__dict__['api'] = db_api.api_from_models()
        return obj

    def jsonify(self, api=None):
        if api is None:
            api = db_api.api_from_models()

        classname = self.__class__.__name__.lower()
        field_list = api._model_get_columns(classname)

        newself = self
        if api != self.api:
            newself = copy.copy(self)
            newself.api = api

        return dict([[c, getattr(newself, c)] for c in field_list])


class Tasks(JsonRenderer, Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey('nodes.id'))
    action = Column(String(40))
    payload = Column(JsonBlob, default={})
    state = Column(
        Enum('pending', 'delivered', 'running',
             'done', 'timeout', 'cancelled'),
        default='pending')
    parent_id = Column(Integer, ForeignKey('tasks.id'), default=None)
    result = Column(JsonBlob, default={})
    submitted = Column(Integer)
    completed = Column(Integer)
    expires = Column(Integer)

    _non_updatable_fields = ['id', 'submitted']

    def __init__(self, node_id, action, payload, state='pending',
                 parent_id=None, result=None, submitted=None, completed=None,
                 expires=None):
        self.node_id = node_id
        self.action = action
        self.payload = payload
        self.state = state
        self.parent_id = parent_id
        self.result = result
        self.submitted = int(time.time())
        self.completed = completed
        self.expires = expires

    def __repr__(self):
        return '<Task %r>' % (self.id)


# set up a listener to auto-populate values in Task struct
@event.listens_for(Tasks.state, 'set')
def task_state_mungery(target, value, oldvalue, initiator):
    non_t = ['pending', 'running', 'delivered']

    if value not in non_t and target.completed is None:
        target.completed = int(time.time())


# This shifts over to in-memory on the backends

# class Primitives(Base):
#     __tablename__ = 'primitives'

#     id = Column(Integer, primary_key=True)
#     name = Column(String(64), unique=True, nullable=False)
#     args = Column(JsonBlob, default={})
#     constraints = Column(JsonBlob, default=[])
#     consequences = Column(JsonBlob, default=[])

#     def __init__(self, name, args=None, constraints=None,
#                  consequences=None):
#         self.name = name
#         self.args = args
#         self.constraints = constraints
#         self.consequences = consequences


class Facts(JsonRenderer, Base):
    __tablename__ = 'facts'
    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    key = Column(String(64), nullable=False)
    value = Column(JsonEntry, default="")
    __table_args__ = (UniqueConstraint('node_id', 'key', name='key_uc'),)

    _non_updatable_fields = ['id', 'node_id', 'key']

    def __init__(self, node_id, key, value=None):
        self.node_id = node_id
        self.key = key
        self.value = value


class Attrs(JsonRenderer, Base):
    __tablename__ = 'attrs'

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    key = Column(String(64), nullable=False)
    value = Column(JsonEntry, default="")
    __table_args__ = (UniqueConstraint('node_id', 'key', name='key_uc'),)

    _non_updatable_fields = ['id', 'node_id', 'key']

    def __init__(self, node_id, key, value=None):
        self.node_id = node_id
        self.key = key
        self.value = value


class Nodes(JsonRenderer, Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    adventure_id = Column(Integer, ForeignKey('adventures.id'))
    task_id = Column(Integer, ForeignKey('tasks.id',
                                         use_alter=True,
                                         name='fk_task_id'), default=None)

    _non_updatable_fields = ['id', 'name']
    _synthesized_fields = ['facts', 'attrs']

    def __init__(self, name,
                 backend=None, backend_state=None,
                 adventure_id=None, task_id=None):
        self.name = name
        self.adventure_id = adventure_id
        self.task_id = task_id

    def __repr__(self):
        return '<Nodes %r>' % (self.name)

    @property
    def facts(self):
        def fact_union(fact, value, parent_value):
            if value is FactDoesNotExist:
                value = []
            if not isinstance(parent_value, list):
                raise ValueError("Union inheritance called on non-list fact:"
                                 "%s" % fact)

            for item in parent_value:
                if not item in value:
                    value.append(item)
            return value

        def fact_parent_clobber(fact, value, parent_value):
            if parent_value:
                return parent_value
            return value

        def fact_child_clobber(fact, value, parent_value):
            if value is not FactDoesNotExist:
                return value
            return parent_value

        def fact_none(fact, value, parent_value):
            return value

        # walk up the parent tree, applying facts downward
        tree = []
        n = self.id
        ns = locals()
        while(n is not None and n not in tree):
            tree.append(n)
            parent = self.api.facts_query(
                'key="parent_id" and node_id=%s' % int(n))
            n = None if len(parent) != 1 else parent[0]['value']

        # okay, we have the tree... apply facts top down
        tree.reverse()

        n = tree.pop(0)
        my_facts = dict(
            [(fact['key'], fact['value'])
             for fact in self.api.facts_query('node_id=%d' % int(n))])

        for n in tree:
            parent_facts = my_facts

            my_facts = dict(
                [(fact['key'], fact['value'])
                 for fact in self.api.facts_query('node_id=%d' % int(n))])

            for parent_k, parent_v in parent_facts.iteritems():
                fact_def = roush.backends.fact_by_name(parent_k)
                f = fact_none
                if not fact_def is None:
                    f = ns["fact_%s" % fact_def['inheritance']]

                my_facts[parent_k] = f(
                    parent_k, my_facts.get(parent_k, FactDoesNotExist),
                    parent_v)

                if my_facts[parent_k] is FactDoesNotExist:
                    del my_facts[parent_k]

        return my_facts

    @property
    def attrs(self):
        return dict([[x['key'], x['value']] for x in
                     self.api._model_query('attrs',
                                           'node_id=%d' % self.id)])


class Adventures(JsonRenderer, Base):
    __tablename__ = 'adventures'
    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    dsl = Column(JsonBlob, default={})
    criteria = Column(String(255))
    args = Column(JsonBlob, default={})

    _non_updatable_fields = ['id']

    def __init__(self, name, dsl, criteria='true', args={}):
        self.name = name
        self.dsl = dsl
        self.criteria = criteria
        self.args = args

    def __repr__(self):
        return '<Adventures %r>' % (self.name)


class Filters(JsonRenderer, Base):
    __tablename__ = 'filters'
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('filters.id'), default=None)
    name = Column(String(30))
    parent = relationship('Filters', remote_side=[id])
    filter_type = Column(String(30))
    expr = Column(String(255))

    _non_updatable_fields = ['id']
    _synthesized_fields = ['full_expr']

    def __init__(self, name, filter_type, expr, parent_id=None):
        self.name = name
        self.parent_id = parent_id
        self.filter_type = filter_type
        self.expr = expr

    def __repr__(self):
        return '<Filter %r>' % (self.name)

    @property
    def full_expr(self):
        if self.parent_id:
            if self.api is None:
                return '(%s) and (%s)' % (self.expr, self.parent.full_expr)
            else:
                parent = self.api._model_get_by_id('filters',
                                                   self.parent_id)
                return '(%s) and (%s)' % (self.expr, parent.full_expr)
        else:
            return self.expr


class Primitives(JsonRenderer, inmemory.InMemoryBase):
    id = inmemory.Column(inmemory.Integer, primary_key=True, nullable=False,
                         required=True)
    name = inmemory.Column(inmemory.String(32), required=True)
    args = inmemory.Column(inmemory.JsonBlob, default={})
    constraints = inmemory.Column(inmemory.JsonBlob, default=[])
    consequences = inmemory.Column(inmemory.JsonBlob, default=[])

    def __init__(self, name, args=None, constraints=None,
                 consequences=None):
        self.name = name
        self.args = args
        self.constraints = constraints
        self.consequences = consequences


class CFactDoesNotExist(object):
    pass

FactDoesNotExist = CFactDoesNotExist()
