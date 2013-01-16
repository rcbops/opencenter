#!/usr/bin/env python

import flask
import generic
import utility

from roush.db.api import api_from_models
from roush.webapp import solver


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

    if not 'node' in data:
        return generic.http_badrequest(msg='node not specified')

    adventure = api._model_get_by_id('adventures', int(adventure_id))

    if adventure is None:
        return generic.http_notfound()

    return generic.http_solver_request(data['node'], [],
                                       api=api, plan=adventure['dsl'])
