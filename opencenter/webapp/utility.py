#!/usr/bin/env python
#               OpenCenter™ is Copyright 2013 by Rackspace US, Inc.
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

import copy
import logging
import time

import gevent.event
import gevent.coros

from opencenter.db.api import api_from_models
from opencenter.webapp import solver


util_conditions = {}
util_locks = {}
util_lock_lock = gevent.coros.Semaphore()

LOG = logging.getLogger(__name__)


def _get_or_make_lock(what):
    """
    Helper function that will retrieve a lock by
    name or create a new one by that name

    Arguments:
    what - lock name

    Returns:
    gevent.coros.Semaphore object
    """

    util_lock_lock.acquire()

    if not what in util_locks:
        util_locks[what] = gevent.coros.Semaphore()

    util_lock_lock.release()

    return util_locks[what]


def lock_acquire(what, timeout=None):
    """
    Acquire a named lock.  This will *always*
    block.  It *may* be called with a timeout.

    Arguments:
    what -- semaphore name
    timeout -- how long to wait for semaphore

    Returns:
    bool - lock acquired

    if returning false with timeout, this almost
    certainly implies timeout.  If not, then something
    really really bad happened, and things will probably
    go sideways soon.
    """
    lock = _get_or_make_lock(what)
    return lock.acquire(blocking=True, timeout=timeout)


def lock_release(what):
    """
    Release a held lock by name

    If one tries to release a lock not held, that
    would be problematic.  Don't do that.

    Arguments:
    what -- name of lock to acquire

    Returns:
    bool -- lock released

    This should really always return true.  Should
    it return false, you are probably likely to
    deadlock.  Soon.
    """
    lock = _get_or_make_lock(what)
    return lock.release()


def _get_or_make_event(what):
    util_lock_lock.acquire()

    if not what in util_conditions:
        util_conditions[what] = gevent.event.Event()

    util_lock_lock.release()

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


def wait(what, timeout=30):
    event = _get_or_make_event(what)
    LOG.debug('waiting on %s' % what)
    event.wait(timeout)
    event.clear()


def sleep(how_long):
    gevent.sleep(how_long)


def is_container(node):
    return 'backends' in node['facts'] and \
        'container' in node['facts']['backends']


def is_leaf(node):
    return not(is_container(node))


def true_f(_):
    return True


def _expand_nodes(nodelist, filter_f=true_f,
                  api=None, depth=0, detailed=False):
    if api is None:
        api = api_from_models()
    final_nodes = []
    nodes = copy.deepcopy(nodelist)
    seen = {}
    for node in nodes:
        if isinstance(node, (int, long)):
            node = api.node_get_by_id(node)
        if not node['id'] in seen:
            seen[node['id']] = {"inspect": False, "level": 0}
        elif not seen[node['id']]['inspect']:
            #We've already inspected this node, move on.
            next
        #We're about to inspect the node.  Don't do it if we see the node again
        seen[node['id']]['inspect'] = False
        if filter_f(node):
            if detailed:
                final_nodes.append(node)
            elif node is not None:
                final_nodes.append(node['id'])
        #We'll add new children provided we're not out of depth
        if is_container(node) and (depth == 0
                                   or seen[node['id']]['level'] < depth):
            new_nodes = api.nodes_query('facts.parent_id = %s' % node['id'])
            for new_n in new_nodes:
                if not new_n['id'] in seen:
                    seen[new_n['id']] = {
                        "inspect": True,
                        "level": seen[node['id']]['level'] + 1}
                    nodes.append(new_n)
    return final_nodes


def expand_nodelist(nodelist, api=None):
    """
    given a list of nodes (including containers),
    generate a fully expanded list of non-container-y
    nodes
    """
    if api is None:
        api = api_from_models()
    return _expand_nodes(nodelist, api=api, filter_f=is_leaf)


def fully_expand_nodelist(nodelist, api=None):
    """
    given a list of nodes (including containers),
    generate a fully expanded list of all node_ids in node_list
    as well as their descendant nodes
    """
    if api is None:
        api = api_from_models()
    return _expand_nodes(nodelist, api=api)


def get_direct_children(node_id, api=None):
    """
    given a node_id, return a list of all direct child nodes
    """
    if api is None:
        api = api_from_models()
    return [x for x in _expand_nodes([node_id], api=api,
                                     depth=1, detailed=True)
            if x['id'] != node_id]


def run_adventure(adventure_dsl=None, nodes=None):
    """
    run an arbitrary adventure on a set of nodes, either by ID or
    as an ad-hoc adventure dsl.

    There are going to be issues with running ad-hoc adventures including
    logging and tracking problems.  these should be straightened out.
    """

    payload = {}
    adv_globals = {}

    payload['adventure_dsl'] = adventure_dsl
    payload['globals'] = adv_globals

    node_list = nodes

    api = api_from_models()

    # we will no longer expand node lists.  At some point
    # we either need hints on adventures for whether they are
    # targetted at nodes or containers, or whether they
    # should be expanded.  Or perhaps offer an API call
    # to expand node lists.  Or something else altogether.

    # LOG.debug('node list before expansion: %s' % nodes)
    # node_list = expand_nodelist(nodes)
    # LOG.debug('node list after expansion: %s' % node_list)

    if len(node_list) == 0:
        raise ValueError('no nodes specified to run on')

    payload['nodes'] = node_list

    # find the node with the adventurator plugin
    query = "'adventurator' in attrs.opencenter_agent_output_modules"

    adventure_nodes = api.nodes_query(query)

    # find out how long this should run...
    max_time = 0
    for step in adventure_dsl:
        max_time += step.get('timeout', 30)

    if len(adventure_nodes) > 0:
        adventure_node = adventure_nodes.pop(0)['id']

        task = api.task_create({'action': 'adventurate',
                                'node_id': adventure_node,
                                'payload': payload,
                                'expires': int(time.time() + max_time)})

        # FAIL: create a task update -- this should be done
        # via the model...
        task_semaphore = 'task-for-%s' % adventure_node
        notify(task_semaphore)
    else:
        raise ValueError('no adventurator')

    return task


def solve_for_node(node_id, constraints, api=None, plan=None):
    """
    given a node id and a list of constraints, run a solver
    to try and find a solution path.

    it returns (is_solvable, requires_input, solution_plan)
    """
    if api is None:
        api = api_from_models()

    if plan is not None:
        task_solver = solver.Solver.from_plan(api, node_id, [], plan)
    else:
        task_solver = solver.Solver(api, node_id, constraints)

    is_solvable, requires_input, solution_plan = task_solver.solve()

    return (is_solvable, requires_input, solution_plan)


def solve_and_run(node_id, constraints, api=None, plan=None):
    if api is None:
        api = api_from_models()
    is_solvable, requires_input, solution_plan = solve_for_node(
        node_id, constraints, api=api, plan=plan)

    task = None

    if is_solvable:
        task = run_adventure(adventure_dsl=solution_plan, nodes=[node_id])

    return task, is_solvable, requires_input, solution_plan


def unprovisioned_container():
    api = api_from_models()
    unprovisioned = api._model_query(
        'nodes',
        'name = "unprovisioned" and "container" in facts.backends')
    if len(unprovisioned) == 0:
        #create unprovisioned node
        unprovisioned = api._model_create(
            'nodes',
            {"name": "unprovisioned"})
        api._model_create(
            'facts',
            {"node_id": unprovisioned['id'],
             "key": "backends",
             "value": ["node", "container"]})
        return unprovisioned
    else:
        unprovisioned = unprovisioned[0]
        return unprovisioned
