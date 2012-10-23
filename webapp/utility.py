#!/usr/bin/env python

import gevent.event

util_conditions = {}


def _get_or_make_event(what):
    if not what in util_conditions:
        util_conditions[what] = gevent.event.Event()

    return util_conditions[what]


def notify(what):
    if what in util_conditions:
        print 'notifying %s' % what
        util_conditions[what].set()
        print 'done notifying %s' % what


def clear(what):
    if what in util_conditions:
        util_conditions[what].clear()


def wait(what):
    event = _get_or_make_event(what)
    print 'waiting for %s' % what
    event.wait()
    event.clear()
    print 'done waiting for %s' % what
