#!/usr/bin/env python

import flask
import generic
import utility

from roush.db.api import api_from_models


api = api_from_models()
object_type = 'adventures'
bp = flask.Blueprint(object_type, __name__)


@bp.route('/', methods=['GET', 'POST'])
def list():
    return generic.list(object_type)


@bp.route('/<object_id>', methods=['GET', 'PUT', 'DELETE'])
def by_id(object_id):
    return generic.object_by_id(object_type, object_id)


@bp.route('/<adventure_id>/execute', methods=['POST'])
def execute_adventure(adventure_id):
    data = flask.request.json
    data['adventure'] = adventure_id

    nodes = utility.expand_nodelist(data['nodes'])
    data['nodes'] = nodes

    # find the node with the adventurator plugin
    query = "'adventurator' in facts.roush_agent_output_modules"

    adventure_nodes = api.nodes_query(query)

    if len(adventure_nodes) > 0:
        adventure_node = adventure_nodes.pop(0)['id']

        task = api.task_create({'action': 'adventurate',
                                'node_id': adventure_node,
                                'payload': data})
        utility.notify('task-for-%s' % adventure_node)

        href = flask.request.base_url + str(task['id'])

        return generic.http_response(201, 'Task Created', task=task,
                                     ref=href)

    return generic.http_response(404, 'cannot find orchestrator')
