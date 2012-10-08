#!/usr/bin/env python

import os
import sys
import logging

LOG = logging.getLogger('backend.driver')


# class BackendException(Exception):
#     pass


# class NodeDoesNotExist(BackendException):
#     pass


# class ClusterDoesNotExist(BackendException):
#     pass


# class RoleDoesNotExist(BackendException):
#     pass


# class BackendError(BackendException):
#     pass


backend_list = {}

# we'll load either a directory or a file, and add any
# loaded backends to the backend list.
#
# still expects
def load(path, config={}):
    if os.path.isdir(path):
        _load_path(path, config)

def backends():
    return backend_list.keys()

def notify(object_type, notification_type, old_object, new_object):
    # evaluate filter predicate, call all registered handlers
    #

    # Punt for now

    # for non-node, notify all backends
    if object_type != 'node':
        backend_notification_list = backend_list.keys()
    else:
        backend_notification_list = [old_object.backend]
        if old_object.backend != new_object.backend:
            backend_notification_list.append(new_object.backend)

    for backend in backend_notification_list:
        backend_list[backend].notify(object_type, notification_type, old_object, new_object)

def _load_path(path, config={}):
    dirlist = os.listdir(path)
    for relpath in dirlist:
        p = os.path.join(path, relpath)

    if not os.path.isdir(p) and p.endswith('.py'):
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
    class_str = '%sBackend' % ''.join(map(lambda x: x.capitalize(), name.split('-')))

    try:
        __import__(import_str)
        return getattr(sys.modules[import_str], class_str)(config[class_str])
    except Exception as e:
        LOG.error('Could not load backend named %s (%s)' % (name, str(e)))

    return None

# Object types: cluster, role, node, &c
# Notification types: create, update, delete
class ConfigurationBackend(object):
    def notify(self, object_type, notification_type, old_object, new_object):
        raise NotImplementedError
