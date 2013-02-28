#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
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

if __name__ == '__main__':
    import os
    import sys
    import copy
    import json

    sys.path.append(os.path.dirname(__file__))

    import logging

    logging.basicConfig(level=logging.DEBUG)

    import opencenter.db.database
    from opencenter.db import api as db_api
    from opencenter.db.database import init_db

    from sqlalchemy.orm import sessionmaker, create_session, scoped_session
    from sqlalchemy.ext.declarative import declarative_base

    from opencenterclient.client import OpenCenterEndpoint

    from opencenter.webapp.ast import FilterBuilder, FilterTokenizer
    from opencenter.webapp.solver import Solver

    ep = OpenCenterEndpoint()

    init_db('sqlite:///opencenter.db')
    db_session = scoped_session(lambda: create_session(autocommit=False,
                                                       autoflush=False,
                                                       bind=engine))

    Base = declarative_base()
    Base.query = db_session.query_property()

    ##########################

    ast_logger = logging.getLogger('opencenter.webapp.ast')
    ast_logger.setLevel(logging.WARNING)

    expr1 = 'facts.woof = "goober"'
    expr2 = 'facts.arf = "woof"'

    api = db_api.api_from_models()

    solver = Solver(api, 4, ['facts.ostype="hi"'])
    solved, requires_input, plan = solver.solve()

    print 'Solver plan: %s' % plan

    solver_from_plan = Solver.from_plan(api, 4,
                                        ['facts.ostype="hi"'],
                                        plan)

    new_plan = solver_from_plan.plan()

    print 'Solver plan: %s' % new_plan

    print 'plans identical: %s' % new_plan == plan

    print plan
    print new_plan

    print json.dumps(solver_from_plan.adventure(), sort_keys=True, indent=4)


    # foo = FilterBuilder(FilterTokenizer(),
    #                     'nodes: "test" in union(facts.blah, "test")')
    # root_node = foo.build()
    # print 'expression: %s' % root_node.to_s()
    # print 'inverted: %s' % root_node.invert()
