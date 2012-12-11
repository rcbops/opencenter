#!/usr/bin/env python

if __name__ == '__main__':
    import os
    import sys
    import copy
    import json

    sys.path.append(os.path.dirname(__file__))

    import logging

    logging.basicConfig(level=logging.DEBUG)

    import roush.db.database
    from roush.db import api as db_api
    from roush.db.database import init_db

    from sqlalchemy.orm import sessionmaker, create_session, scoped_session
    from sqlalchemy.ext.declarative import declarative_base

    from roushclient.client import RoushEndpoint

    from roush.webapp.ast import FilterBuilder, FilterTokenizer
    from roush.webapp.solver import Solver

    ep = RoushEndpoint()

    init_db('sqlite:///roush.db')
    db_session = scoped_session(lambda: create_session(autocommit=False,
                                                       autoflush=False,
                                                       bind=engine))

    Base = declarative_base()
    Base.query = db_session.query_property()

    ##########################

    ast_logger = logging.getLogger('roush.webapp.ast')
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
