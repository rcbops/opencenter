#!/usr/bin/env python

import logging
import os
import sys
import traceback

LOG = logging.getLogger('backend.driver')


class BackendException(Exception):
    pass


class NodeDoesNotExist(BackendException):
    pass


class ClusterDoesNotExist(BackendException):
    pass


class BackendError(BackendException):
    pass


backend_list = {}


# we'll load either a directory or a file, and add any
# loaded backends to the backend list.
#
# still expects
def load(path, config={}):
    LOG.debug('Loading backends from %s' % path)
    if os.path.isdir(path):
        _load_path(path, config)
    else:
        _load_file(path, config)


def backends():
    return backend_list.keys()


def notify(otype, ntype, old_object, new_object):
    # evaluate filter predicate, call all registered handlers
    #

    # Punt for now

    # for non-node, notify all backends

    LOG.debug('Got "%s" for "%s"' % (ntype, otype))

    backend_notification_list = []

    if otype == 'node':
        old_backend = None
        new_backend = None

        if old_object and 'backend' in old_object:
            backend_notification_list.append(old_object['backend'])

        if new_object and 'backend' in new_object:
            backend_notification_list.append(new_object['backend'])
    else:
        backend_notification_list = backend_list.keys()

    try:
        for backend in backend_notification_list:
            if backend in backend_list:
                backend_list[backend].notify(otype, ntype,
                                             old_object, new_object)
    except:
        LOG.info(traceback.format_exc())
        raise BackendError

def _load_path(path, config={}):
    dirlist = os.listdir(path)
    for relpath in dirlist:
        p = os.path.join(path, relpath)

        # how do you pep8 this right?
        if not os.path.isdir(p) and p.endswith('.py'):
            if not p.startswith('__'):
                _load_file(p, config)


def _load_file(path, config={}):
    LOG.debug('Loading backend plugin file %s' % path)

    backend_name = os.path.basename(path).rsplit('.')[0]
    backend_obj = _ns_load(backend_name, config)

    if not backend_obj:
        LOG.debug('Skipping backend %s' % backend_name)
    else:
        backend_list[backend_name] = backend_obj


def _ns_load(name, config={}):
    # expects an include of backends/#{name}.py,
    # with a class of #{name.capitalize}Backend

    import_str = "backends.%s" % name
    class_str = '%sBackend' % ''.join(map(lambda x: x.capitalize(),
                                          name.split('-')))

    try:
        __import__(import_str)
        return getattr(sys.modules[import_str], class_str)(config[class_str])
    except Exception as e:
        LOG.error('Could not load backend "%s"' % name)

    return None


# Object types: cluster, role, node, &c
# Notification types: create, update, delete
class ConfigurationBackend(object):
    def notify(self, object_type, notification_type, old_object, new_object):
        pass
