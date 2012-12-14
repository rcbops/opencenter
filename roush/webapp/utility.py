#!/usr/bin/env python

import logging
import gevent.event

import solver
from roush.db.api import api_from_models

api = api_from_models()
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


def expand_nodelist(nodelist, api=api):
    """
    given a list of nodes (including containers),
    generate a fully expanded list of non-container-y
    nodes
    """

    final_nodelist = []

    for node_id in nodelist:
        node = api.node_get_by_id(node_id)
        is_container = False
        if 'backends' in node['facts'] and \
                'container' in node['facts']['backends']:
            is_container = True

        if not is_container:
            final_nodelist.append(node_id)
        else:
            query = 'parent_id = %s' % node_id
            child_nodes = api.nodes_query(query)
            child_node_ids = [x['id'] for x in child_nodes]

            final_nodelist += expand_nodelist(child_node_ids)

    return final_nodelist


def run_adventure(adventure_id=None, adventure_dsl=None, nodes=None):
    """
    run an arbitrary adventure on a set of nodes, either by ID or
    as an ad-hoc adventure dsl.

    There are going to be issues with running ad-hoc adventures including
    logging and tracking problems.  these should be straightened out.
    """

    payload = {}

    if adventure_id:
        payload['adventure'] = adventure_id
    elif adventure_dsl:
        payload['adventure_dsl'] = adventure_dsl

    node_list = expand_nodelist(nodes)
    if len(node_list) == 0:
        raise ValueError('no nodes specified to run on')

    payload['nodes'] = node_list

    # find the node with the adventurator plugin
    query = "'adventurator' in facts.roush_agent_output_modules"

    adventure_nodes = api.nodes_query(query)

    if len(adventure_nodes) > 0:
        adventure_node = adventure_nodes.pop(0)['id']

        task = api.task_create({'action': 'adventurate',
                                'node_id': adventure_node,
                                'payload': payload})
    else:
        raise ValueError('no adventurator')

    return task


def solve_for_node(node_id, constraints, api=api):
    """
    given a node id and a list of constraints, run a solver
    to try and find a solution path.

    it returns (is_solvable, requires_input, solution_plan, adventure)
    """

    task_solver = solver.Solver(api, node_id, constraints)
    is_solvable, requires_input, solution_plan = task_solver.solve()
    adventure = None

    if is_solvable:
        adventure = task_solver.adventure()

    return (is_solvable, requires_input, solution_plan, adventure)

def solve_and_run(node_id, constraints, api=api):
    is_solvable, requires_input, solution_plan, adventure = solve_for_node(
        node_id, constraints, api)

    task = None

    if is_solvable:
        task = run_adventure(adventure_dsl=adventure, nodes=[node_id])

    return task
