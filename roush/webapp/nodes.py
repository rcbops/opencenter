#!/usr/bin/env python

import flask
import generic

from roush.db import api

from roush.webapp import ast
from roush.webapp import utility
from roush.webapp import errors
from roush.webapp import auth

object_type = 'nodes'
bp = flask.Blueprint(object_type,  __name__)


@bp.route('/', methods=['GET', 'POST'])
def list():
    return generic.list(object_type)


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)


@bp.route('/<node_id>/tasks_blocking', methods=['GET'])
def tasks_blocking_by_node_id(node_id):
    task = api.task_get_first_by_filter({'node_id': node_id,
                                         'state': 'pending'})
    while not task:
        semaphore = 'task-for-%s' % node_id
        flask.current_app.logger.debug('waiting on %s' % semaphore)
        utility.wait(semaphore)
        task = api.task_get_first_by_filter({'node_id': node_id,
                                             'state': 'pending'})
        if task:
            utility.clear(semaphore)

    result = flask.jsonify({'task': task})
    task['state'] = 'delivered'
    api._model_update_by_id('tasks', task['id'], task)
    return result


@bp.route('/<node_id>/tasks', methods=['GET'])
def tasks_by_node_id(node_id):
    # Display only tasks with state=pending
    task = api.task_get_first_by_filter({'node_id': node_id,
                                         'state': 'pending'})
    if not task:
        return generic.http_notfound()
    else:
        resp = generic.http_response(task=task)
        task['state'] = 'delivered'
        api._model_update_by_id('tasks', task['id'], task)
        return resp


@bp.route('/<node_id>/adventures', methods=['GET'])
def adventures_by_node_id(node_id):
    node = api.node_get_by_id(node_id)
    if not node:
        return errors.http_not_found()
    else:
        all_adventures = api.adventures_get_all()
        available_adventures = []
        for adventure in all_adventures:
            builder = ast.FilterBuilder(ast.FilterTokenizer(),
                                        adventure['criteria'])
            try:
                root_node = builder.build()
                if root_node.eval_node(node, builder.functions):
                    available_adventures.append(adventure)
            except Exception as e:
                flask.current_app.logger.warn(
                    'adv err %s: %s' % (adventure['name'], str(e)))

        # adventures = api.adventures_get_by_node_id(node_id)
        resp = flask.jsonify({'adventures': available_adventures})
    return resp


@bp.route('/<node_id>/tree', methods=['GET'])
def tree_by_id(node_id):
    seen_nodes = []

    def fill_children(node_hash):
        node_id = node_hash['id']

        children = api._model_get_by_filter(
            'nodes', {'parent_id': node_id})

        for child in children:
            if child['id'] in seen_nodes:
                flask.current_app.logger.error("Loop detected in data model")
            else:
                seen_nodes.append(child['id'])

                if not 'children' in node_hash:
                    node_hash['children'] = []

                node_hash['children'].append(child)
                fill_children(child)

    node = api.node_get_by_id(node_id)
    seen_nodes.append(node_id)

    if not node:
        return generic.http_notfound()
    else:
        fill_children(node)
        resp = generic.http_response(tree=node)
        return resp
