#!/usr/bin/env python

import flask

from roush.db import api
from roush.db import exceptions

from roush.webapp import ast
from roush.webapp import utility
from roush.webapp import errors
from roush.webapp import auth
from functools import partial

nodes = flask.Blueprint('nodes', __name__)

#all node activities require authentication


@nodes.route('/', methods=['GET', 'POST'])
@auth.requires_auth(roles=["admin", "user", "machine"])
def list_nodes():
    if flask.request.method == 'POST':
        data = flask.request.json

        if not 'name' in data:
            return errors.http_bad_request('missing necessary fields')

        try:
            node = api.node_create(data)
            href = flask.request.base_url + str(node['id'])
            msg = {'status': 201,
                   'message': 'Node Created',
                   'node': node,
                   'ref': href}
            resp = flask.jsonify(msg)
            resp.status_code = 201
            resp.headers['Location'] = href
        except exceptions.CreateError as e:
            return errors.http_bad_request(e.message)
    else:
        nodes = api.nodes_get_all()
        resp = flask.jsonify({'nodes': nodes})
    return resp


@nodes.route('/<node_id>/tasks_blocking', methods=['GET'])
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


@nodes.route('/<node_id>/tasks', methods=['GET', 'PUT'])
def tasks_by_node_id(node_id):
    # Display only tasks with state=pending
    task = api.task_get_first_by_filter({'node_id': node_id,
                                         'state': 'pending'})
    if not task:
        return errors.http_not_found()
    else:
        resp = flask.jsonify({'task': task})
        task['state'] = 'delivered'
        api._model_update_by_id('tasks', task['id'], task)
        return resp


@nodes.route('/<node_id>/adventures', methods=['GET'])
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


@nodes.route('/<node_id>/<key>', methods=['GET', 'PUT'])
def attributes_by_node_id(node_id, key):
    node = api.node_get_by_id(node_id)
    if not node:
        return errors.http_not_found()
    else:
        if flask.request.method == 'PUT':
            if key in ['id', 'name']:
                msg = "Attribute %s is not modifiable" % key
                return errors.http_bad_request(msg)
            else:
                if key not in flask.request.json:
                    msg = "Empty body"
                    return http_bad_request(msg)
                else:
                    data = {key: flask.request.json[key]}
                    updated_node = api.node_update_by_id(node_id, data)
                    msg = {'status': 200,
                           'node': updated_node,
                           'message': 'Updated Attribute: %s' % key}
                    resp = flask.jsonify(msg)
                    resp.status_code = 200
        else:
            resp = flask.jsonify({key: node[key]})
        return resp


@nodes.route('/<node_id>/tree', methods=['GET'])
def tree_by_id(node_id):
    recurse = 'recurse' in flask.request.args
    seen_nodes = []

    def fill_children(node_hash):
        node_id = node_hash['id']

        children = api._model_get_by_filter(
            'nodes', {'parent_id': node_id})

        for child in children:
            if child['id'] in seen_nodes:
                self.logger.error("Loop detected in data model")
            else:
                seen_nodes.append(child['id'])

                if not 'children' in node_hash:
                    node_hash['children'] = []

                node_hash['children'].append(child)
                fill_children(child)

    node = api.node_get_by_id(node_id)
    seen_nodes.append(node_id)

    if not node:
        return errors.http_not_found()
    else:
        fill_children(node)
        resp = flask.jsonify({'tree': node})
        return resp


@nodes.route('/<node_id>', methods=['GET', 'PUT', 'DELETE'])
def node_by_id(node_id):
    if flask.request.method == 'PUT':
        data = flask.request.json
        node = api.node_update_by_id(node_id, data)
        resp = flask.jsonify({'node': node})
        return resp
    elif flask.request.method == 'DELETE':
        try:
            node = api.node_get_by_id(node_id)
            if api.node_delete_by_id(node_id):
                msg = {'status': 200, 'message': 'Node deleted'}
                resp = flask.jsonify(msg)
                resp.status_code = 200
                return resp
        except exceptions.NodeNotFound:
            return errors.http_not_found()
    else:
        # node = api.node_get_by_filter({'id': node_id})
        node = api.node_get_by_id(node_id)

        if not node:
            return errors.http_not_found()
        else:
            resp = flask.jsonify({'node': node})
            return resp
