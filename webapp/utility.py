#!/usr/bin/env python

import gevent.event

util_conditions = {}


def _get_or_make_event(what):
    if not what in util_conditions:
        util_conditions[what] = gevent.event.Event()

    return util_conditions[what]


def notify(what):
    if what in util_conditions:
        util_conditions[what].set()


def clear(what):
    if what in util_conditions:
        util_conditions[what].clear()


def wait(what):
    event = _get_or_make_event(what)
    event.wait()
    event.clear()


def expand_nodelist(nodelist):
    return nodelist
