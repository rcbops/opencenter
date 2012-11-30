#!/usr/bin/env python

import logging
import gevent.event


util_conditions = {}
LOG = logging.getLogger(__name__)


def _get_or_make_event(what):
    if not what in util_conditions:
        util_conditions[what] = gevent.event.Event()

    return util_conditions[what]


def notify(what):
    if what in util_conditions:
        LOG.debug('notifying %s' % what)
        util_conditions[what].set()
    else:
        LOG.debug('no waiters on %s... skipping' % what)


def clear(what):
    if what in util_conditions:
        util_conditions[what].clear()


def wait(what):
    event = _get_or_make_event(what)
    LOG.debug('waiting on %s' % what)
    event.wait()
    event.clear()


def expand_nodelist(nodelist):
    return nodelist
