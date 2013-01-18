#!/usr/bin/env python

import flask

from roush.db.api import api_from_models
from roush.webapp import generic
from roush.webapp import utility

api = api_from_models()
bp = flask.Blueprint('plan', __name__)


@bp.route('/', methods=['POST'])
def run_plan():
    # this comes in just like an optioned plan.  We'll stuff any returned
    # args and call it a plan.  <rimshot>
    #

    data = flask.request.json

    if not 'node' in data:
        return generic.http_badrequest(msg='no node specified')

    if not 'plan' in data:
        return generic.http_badrequest(msg='no plan specified')

    plan = data['plan']

    # this is more than a bit awkward
    for step in plan:
        if 'args' in step:
            for arg in step['args']:
                if 'value' in step['args'][arg]:
                    step['ns'][arg] = step['args'][arg]['value']

            step.pop('args')

    # now our plan is a standard plan.  Let's run it
    return generic.http_solver_request(data['node'], [], api=api, plan=plan)
