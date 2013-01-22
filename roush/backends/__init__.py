#!/usr/bin/env python

import json
import logging
import os
import sys


backend_objects = {}
backend_primitives = {}


class Backend(object):
    def __init__(self, path):
        self.facts = []
        self.primitives = []
        classname = self.__class__.__name__.lower()

        backend = os.path.basename(os.path.dirname(path))

        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug('Initializing')

        my_path = os.path.dirname(path)
        json_path = os.path.join(my_path, 'primitives.json')
        fact_path = os.path.join(my_path, 'facts.json')

        self.base_path = my_path

        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                self.primitives = json.loads(f.read())

        if os.path.exists(fact_path):
            with open(fact_path, 'r') as f:
                self.facts = normalize_facts(json.loads(f.read()),
                                             backend)

    def additional_constraints(self, api, node_id, action, ns):
        return []

    def fact_template(self, fact, converger):
        paths = [
            "%s/map/fact-%s-%s.templ" % (self.base_path, fact, converger),
            "%s/map/default.%s.templ" % (self.base_path, converger)]

        for path in paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read()

        return None


def additional_constraints(api, node_id, primitive_id, ns):
    if not primitive_id in backend_primitives:
        raise ValueError('bad primitive id %s' % primitive_id)

    primitive = backend_primitives[primitive_id]
    fullname = primitive['name']

    backend, primitive = fullname.split('.')
    backend_obj = backend_objects[backend]
    return backend_obj.additional_constraints(api, node_id, primitive, ns)


def backend_by_name(backend_name):
    if backend_name in backend_objects:
        return backend_objects[backend_name]
    return None


def fact_by_name(fact_name):
    for backend in backend_objects:
        if fact_name in backend_objects[backend].facts:
            return backend_objects[backend].facts[fact_name]
    return None


def primitive_by_name(primitive_name):
    if not '.' in primitive_name:
        return None

    backend, primitive = primitive_name.split('.')
    if not backend in backend_objects:
        return None

    backend_obj = backend_objects[backend]
    fn = getattr(backend_obj, primitive, None)

    return fn


def load_specific_backend(import_str, class_str):
    """
    load a backend given an import path and a classname.
    e.g. load_specific_backend('roush.backends.foo', 'FooBackend')

    as a side effect, will register facts and primitives in the
    newly loaded class
    """

    __import__(import_str)

    friendly_name = import_str.split('.')[-1].lower()

    obj = getattr(sys.modules[import_str], class_str)()

    backend_objects[friendly_name] = obj

    for primitive, primdata in obj.primitives.items():
        mangled_name = '%s.%s' % (friendly_name, primitive)
        synthetic_id = hash(mangled_name) & 0xFFFFFFFF

        if synthetic_id in backend_primitives:
            raise ValueError('duplicate primitive ID (%s).  %s vs %s' %
                             (synthetic_id, mangled_name,
                              backend_primitives[synthetic_id]['name']))

        backend_primitives[synthetic_id] = {}
        backend_primitives[synthetic_id]['name'] = mangled_name
        backend_primitives[synthetic_id]['id'] = synthetic_id

        for key in primdata:
            backend_primitives[synthetic_id][key] = \
                primdata[key]

        if not 'weight' in backend_primitives[synthetic_id]:
            backend_primitives[synthetic_id]['weight'] = 50


def load():
    """
    walk through all the subdirectories under backends, trying to find
    real python modules, instantiating them as backends
    """

    if len(backend_objects) > 0:
        return

    for file_name in os.listdir(os.path.dirname(__file__)):
        full_path = os.path.join(os.path.dirname(__file__), file_name)
        init_path = os.path.join(full_path, '__init__.py')
        if os.path.isdir(full_path) and os.path.exists(init_path):
            import_str = 'roush.backends.%s' % file_name
            class_str = '%sBackend' % ''.join(map(lambda x: x.capitalize(),
                                                  file_name.split('-')))
            load_specific_backend(import_str, class_str)


def normalize_facts(facts, backend):
    result = {}
    for fact in facts:
        result.update(normalize_fact(fact, backend))
    return result


def normalize_fact(proposed, backend):
    if isinstance(proposed, basestring):
        fact = {proposed: {}}
        name = proposed
    elif not isinstance(proposed, dict) or len(proposed) > 1:
        raise ValueError('Not a valid fact: %s' % proposed)
    else:
        #proposed is a dictionary
        name = proposed.keys()[0]
        fact = {name: {}}
        fact.update(proposed)
        if not isinstance(fact[name], dict):
            raise ValueError('Not a valid fact %s' % proposed)

    fact[name]['inheritance'] = fact[name].get('inheritance', 'parent_clobber')
    fact[name]['type'] = fact[name].get('type', 'untyped')
    fact[name]['settable'] = fact[name].get('settable', True)
    fact[name]['backend'] = backend
    fact[name]['converge'] = fact[name].get('converge', False)
    fact[name]['cluster_wide'] = fact[name].get('cluster_wide', False)
    return fact
