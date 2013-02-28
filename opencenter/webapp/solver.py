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

import copy
import logging
import re

import gevent

import opencenter.backends
from opencenter.db import api as db_api
from opencenter.webapp import ast


class Solver:
    def __init__(self, api, node_id, constraints,
                 parent=None, prim=None, ns=None, applied_consequences=None):

        self.constraints = copy.deepcopy([api.regularize_expression(x)
                                          for x in constraints])
        self.node_id = node_id
        self.base_api = api
        self.applied_consequences = copy.deepcopy(applied_consequences) if \
            applied_consequences is not None else []

        self.children = []
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.parent = parent
        self.prim = prim
        self.task_primitives = {}
        self.adventures = []
        self.ns = ns if ns is not None else {}

        self.logger.info('New solver for constraints %s' % constraints)
        self.logger.info('With applied constraints %s' % applied_consequences)

        # roll the applied consequences forward in an ephemeral
        # api, and do our resolution from that.
        self.api = db_api.ephemeral_api_from_api(self.base_api)
        pre_node = self.api._model_get_by_id('nodes', self.node_id)

        for consequence in self.applied_consequences:
            node = self.api._model_get_by_id('nodes', self.node_id)
            ast.apply_expression(node, consequence, self.api)

        # get rid of constraints we've already solved
        self.constraints = [x for x in self.constraints if not
                            self._constraint_satisfied(x)]

        node = self.api._model_get_by_id('nodes', self.node_id)

        # grab the tasks published from this node as possible primitives
        # ...
        # we aren't actually solving through tasks and adventures
        # yet, but likely have the need
        if 'opencenter_agent_actions' in node['attrs'] and \
                'backends' in node['facts'] and \
                'agent' in node['facts']['backends']:
            for task_name in node['attrs']['opencenter_agent_actions']:
                mangled_name = task_name
                task = node['attrs']['opencenter_agent_actions'][task_name]

                id = hash(mangled_name) & 0xFFFFFFFF
                # should verify this unique against backends
                self.task_primitives[id] = {}
                self.task_primitives[id]['id'] = id
                self.task_primitives[id]['name'] = mangled_name
                self.task_primitives[id]['task_name'] = task_name
                self.task_primitives[id]['constraints'] = \
                    task['constraints']
                self.task_primitives[id]['consequences'] = \
                    task['consequences']
                self.task_primitives[id]['args'] = task['args']
                self.task_primitives[id]['weight'] = 50
                self.task_primitives[id]['timeout'] = task['timeout'] if \
                    'timeout' in task else 30

        self.logger.debug('Node before applying consequences: %s' % pre_node)
        self.logger.debug('Applied consequences: %s' %
                          self.applied_consequences)
        # ephemeral_node = self.api._model_get_by_id('nodes', self.node_id)
        self.logger.debug('Node after applying consequences: %s' % node)

    @classmethod
    def from_plan(cls, api, node_id, constraints, plan,
                  applied_consequences=None):
        root_solver = Solver(api, node_id, constraints,
                             applied_consequences=applied_consequences)
        current_node = root_solver

        for plan_item in plan:
            current_node.solve_one(plan_item)
            if len(current_node.children) != 1:
                raise ValueError("Couldn't apply plan")

            current_node = current_node.children[0]

        if len(current_node.children) != 0:
            raise ValueError("Plan didn't satisfy constraints")

        return root_solver

    # we need to dummy up the primitives to add the node tasks
    # to them.  This is something of a fail.  Maybe we could
    # dummy this up in the model somehow?
    def _get_all_primitives(self):
        primitive_list = self.api._model_get_all('primitives')
        #
        # we are not solving over tasks anymore - we need to rethink this
        # plus, it's a stoopid generator.
        #
        primitive_list += self.task_primitives.values()
        return primitive_list

    def _get_primitive_by_name(self, name):
        primitives = self.api._model_query(
            'primitives',
            'name="%s"' % name)

        if len(primitives) > 0:
            return primitives[0]

        # walk through the self.task_primitives
        primitives = [self.task_primitives[x] for x in
                      self.task_primitives if
                      self.task_primitives[x]['name'] == name]
        if len(primitives) > 0:
            return primitives[0]

        return None

    def _get_additional_constraints(self, primitive_id, ns):
        if primitive_id in self.task_primitives:
            return []
        else:
            return opencenter.backends.additional_constraints(self.api,
                                                              self.node_id,
                                                              primitive_id,
                                                              ns)

    def _build_constraints(self, constraints):
        """
        build asts of constraints and their inverted consequences.

        in addition, this flattens the list of constraints, de-joining
        any AND constraints.
        """

        retval = []
        f_builder = ast.FilterBuilder(ast.FilterTokenizer())

        for constraint in constraints:
            f_builder.set_input(constraint)
            constraint_node = f_builder.build()
            for consequence in constraint_node.invert():
                # now, we'll re-invert the consequence to get
                # the flattened constraint, and associate it
                # with a consequence.
                f_builder.set_input(consequence)
                consequence_ast = f_builder.build()
                constraint_list = consequence_ast.invert()
                if len(constraint_list) != 1:
                    raise RuntimeError('too many constraints?')  # cannot be
                constraint = constraint_list[0]
                f_builder.set_input(constraint)
                constraint_ast = f_builder.build()

                retval.append({'constraint': constraint,
                               'constraint_ast': constraint_ast,
                               'consequence': consequence,
                               'consequence_ast': consequence_ast})

        return retval

    def _constraint_satisfied(self, constraint):
        """see if the node in question already meets the constraint"""
        full_node = self.api._model_get_by_id('nodes', self.node_id)

        builder = ast.FilterBuilder(ast.FilterTokenizer(),
                                    constraint,
                                    'nodes', api=self.api)
        root_node = builder.build()
        return root_node.eval_node(full_node)

    def _can_meet_constraints(self, primitive):
        """see if the node in question meets the primitive constraints"""
        self.logger.debug('Can I meet constraints on %s?' % primitive)
        can_add = True

        self.logger.debug('current primitive: %s' % primitive)

        if primitive['constraints'] != []:
            constraint_filter = ' AND '.join(map(lambda x: '(%s)' % x,
                                                 primitive['constraints']))

            can_add = self._constraint_satisfied(constraint_filter)
        self.logger.debug('Answer: %s' % can_add)
        return can_add

    def can_coerce(self, constraint_node, consequence_node):
        # see if the consequence expression can be forced
        # into the constraint form.

        # this really needs to be generalized

        self.logger.debug('Trying to coerce %s' % consequence_node.to_s())
        self.logger.debug('... to %s' % constraint_node.to_s())

        # ugly special case on union
        if constraint_node.op == 'FUNCTION' and \
                constraint_node.lhs == 'union' and \
                consequence_node.op == 'FUNCTION' and \
                consequence_node.lhs == 'union':
            self.logger.debug('doing union constraint')

            if constraint_node.rhs[0].op == 'IDENTIFIER' and \
                    consequence_node.rhs[0].op == 'IDENTIFIER' and \
                    constraint_node.rhs[0].lhs == consequence_node.rhs[0].lhs:

                can_constrain, ns = self.can_coerce(constraint_node.rhs[1],
                                                    consequence_node.rhs[1])

                return can_constrain, ns
            else:
                self.logger.debug('different arrays (%s, %s)' %
                                  (consequence_node.rhs[0],
                                   constraint_node.rhs[0]))
            return False, {}

        if constraint_node.op not in ['IDENTIFIER', 'STRING',
                                      'NUMBER', 'BOOL']:
            self.logger.debug('Cannot coerce vars not ID, STRING, NUM, BOOL:'
                              ' %s' % constraint_node.op)
            return False, {}

        if consequence_node.op not in ['IDENTIFIER', 'STRING',
                                       'NUMBER', 'BOOL']:
            self.logger.debug('Cannot coerce vars not ID, STRING, NUM, BOOL:'
                              ' %s' % consequence_node.op)
            return False, {}

        # if consequence_node.op != constraint_node.op:
        #     self.logger.debug('Cannot coerce dissimilar op types: %s != %s' %
        #                       (consequence_node.op, constraint_node.op))
        #     return False, {}

        str_consequence = str(consequence_node.lhs)
        str_constraint = str(constraint_node.lhs)

        if str_consequence == str_constraint and \
                consequence_node.op == constraint_node.op:
            self.logger.debug('Equal literals!  Success!')
            return True, {}

        match = re.match("(.*)\{(.*?)}(.*)", str_consequence)
        if match is None:
            self.logger.debug('dissimilar literals')
            return False, {}

        if not str_constraint.startswith(match.group(1)) or \
                not str_constraint.endswith(match.group(3)):
            self.logger.debug('cant coerce even with var binding')
            return False, {}

        key = match.group(2)
        value = str_constraint[len(match.group(1)):]
        if len(match.group(3)):
            value = value[:-len(match.group(3))]

        return True, {key: value}

    def can_solve(self, constraint_ast, consequence_ast):
        conseq_string = consequence_ast.to_s()
        constr_string = constraint_ast.to_s()

        self.logger.debug('are "%s" and "%s" ast-illy identical?' %
                          (conseq_string, constr_string))

        # for a consequence to be _real_, it must do something.
        # so something must be assigned to something, or at the minimum,
        # some expression must be assigned to a (potentially expanded)
        # symbol

        if constraint_ast.op != consequence_ast.op:
            self.logger.debug('Cannot solve: op types different')
            return False, {}

        if constraint_ast.op != ':=':
            self.logger.debug('Cannot solve: op type is not :=')
            return False, {}

        # see if the "assigned" expression (lhs) is (or can be coerced)
        # into the other lhs.
        can_coerce_lhs, ns_lhs = self.can_coerce(constraint_ast.lhs,
                                                 consequence_ast.lhs)

        can_coerce_rhs, ns_rhs = self.can_coerce(constraint_ast.rhs,
                                                 consequence_ast.rhs)

        if not can_coerce_rhs or not can_coerce_lhs:
            return False, {}

        self.logger.debug('lhs bindings: %s' % ns_lhs)
        self.logger.debug('rhs bindings: %s' % ns_rhs)

        key_union = [x for x in ns_lhs.keys() if x in ns_rhs.keys()]
        for key in key_union:
            if ns_rhs[key] != ns_lhs[key]:
                self.logger.debug('cannot solve %s = %s AND %s' %
                                  (key, ns_rhs[key], ns_lhs[key]))

                return False, {}

        for key in ns_rhs.keys():
            ns_lhs[key] = ns_rhs[key]

        self.logger.debug("Yes, they are!  With ns: %s" % ns_lhs)
        return True, ns_lhs

    def _is_forwarding_solution(self, primitive, constraints, ns=None):
        """
        see if a primitive with a particular namespace binding
        can actually satisfy a constraint (mostly for plan
        testing)
        """

        if ns is None:
            ns = {}

        potential = self._potential_solutions(primitive, constraints)
        if len(potential) == 1:
            return potential[0]

        for solution in potential:
            if ns == solution['ns']:
                return solution

        return None

    def _potential_solutions(self, primitive, constraints):
        """see if a primitive can satisfy any solver constraint

        primitive -- primitive db object (dict) to test
        constraints -- list of constraint structures
                       (as from _build_constraints) that must be
                       satisfied
        """

        self.logger.debug('Can %s solve any constraints %s?' %
                          (primitive['name'],
                           [x['constraint'] for x in constraints]))

        f_builder = ast.FilterBuilder(ast.FilterTokenizer())
        valid_solutions = []

        for constraint in constraints:
            # walk through the constraints and see if the
            # primitive can solve this constraint with
            # any namespace binding.
            constraint_ast = constraint['consequence_ast']

            for consequence in primitive['consequences']:
                f_builder.set_input(consequence)
                consequence_ast = f_builder.build()

                satisfies, req_ns = self.can_solve(constraint_ast,
                                                   consequence_ast)
                if satisfies:
                    solution = {'primitive': primitive,
                                'ns': req_ns,
                                'solves': constraint['constraint'],
                                'consequence': constraint['consequence']}
                    valid_solutions.append(solution)

        self.logger.debug('Answer: %s' % valid_solutions)
        return valid_solutions

    def solve_one(self, proposed_plan=None):
        """
        run a single pass of the solver, trying to find all the
        available primitives that can solve any existing constraint.
        """

        self.logger.debug("solving %s with plan %s" % (self.constraints,
                                                       proposed_plan))
        # first, build up asts of all my unsolved constraints
        constraint_list = self._build_constraints(self.constraints)

        # fix/regularize our internal constraint list
        self.constraints = [x['constraint'] for x in constraint_list]

        self.logger.info('New solver for constraints: %s (plan: %s)' %
                         (self.constraints, proposed_plan))

        # walk through all the primitives, and see what primitives
        # have constraints that are met, and spin off a new solver
        # from that state.

        primitives = []

        if proposed_plan:
            # fix this up so it looks more like it used to.  ;)
            prim_item = self._get_primitive_by_name(proposed_plan['primitive'])
            if prim_item:
                primitives = [prim_item]
            # primitives = self.api._model_query(
            #     'primitives',
            #     'name="%s"' % proposed_plan['primitive'])
        else:
            primitives = self._get_all_primitives()

            # strip out the primitives that won't solve anything
            primitives = [x for x in primitives if
                          x['consequences'] != []]
            primitives = [x for x in primitives
                          if self._can_meet_constraints(x)]

        # get all the primitives capable of being run, given the
        # primitive constraints

        # see if any of the appliable primitives have consequences that
        # could forward us to our goal.
        all_solutions = []

        if len(primitives) == 0:
            # we can't meet constraints of any primitives, or we specified
            # a bogus primitive in a plan...
            self.logger.debug('no valid primitives')
            return None

        if proposed_plan:
            # plan_prim = primitives[0]
            plan_ns = proposed_plan['ns']

            primitive = primitives[0]

            # primitive = self.api._model_get_by_id(
            #     'primitives',
            #     plan_prim['id'])

            solution = self._is_forwarding_solution(primitive,
                                                    constraint_list,
                                                    plan_ns)
            if not solution:
                solution = {'primitive': primitive,
                            'ns': plan_ns,
                            'solves': None,
                            'consequence': None}

                # self.logger.debug('plan item: %s' % proposed_plan)
                # self.logger.debug('constraint_list: %s' % constraint_list)
                # raise ValueError('Bad plan: %s does not forward' %
                #                  plan_prim['name'])

            all_solutions = [solution]
        else:
            for primitive in primitives:
                solutions = self._potential_solutions(primitive,
                                                      constraint_list)
                all_solutions += solutions

        # Now that we know all possible solutions, let's
        # spin up sub-solvers so we can continue to work
        # through them.
        self.logger.info("Found %d helpful solutions: %s" %
                         (len(all_solutions),
                         [x['primitive']['name'] for x in all_solutions]))

        ###
        # This might be invalid, but we'll classify all solutions into
        # one of two groups -- those that have discovered consequences,
        # and those that don't.  Those that don't, we'll consider
        # interchangable, and just choose one.
        #
        # This might not be right.
        #
        unconstrained_solutions = []
        constrained_solutions = []

        if not proposed_plan:
            for solution in all_solutions:
                solution['discovered'] = self._get_additional_constraints(
                    solution['primitive']['id'],
                    solution['ns'])

                if solution['discovered'] is None:
                    # we'll just drop it
                    self.logger.debug(
                        'Cannot solve %s due to addl constraints' %
                        (solution['primitive']['name'], ))
                    pass
                elif len(solution['discovered']) != 0:
                    constrained_solutions.append(solution)
                else:
                    unconstrained_solutions.append(solution)

            candidate_solutions = constrained_solutions
            if len(unconstrained_solutions) > 0:
                candidate_solutions.append(unconstrained_solutions[0])
        else:
            candidate_solutions = all_solutions

        self.logger.info('All candidate solutions: %s' % candidate_solutions)

        for solution in candidate_solutions:
            # yield for gevent
            gevent.sleep(0)

            self.logger.info("%s with %s, solving %s" %
                             (solution['primitive']['name'],
                              solution['ns'],
                              solution['solves']))

            constraints = copy.deepcopy(self.constraints)
            applied_consequences = copy.deepcopy(self.applied_consequences)

            # if not solution['solves'] in constraints:
            #     raise RuntimeError('constraint disappeared?!?!')

            # get additional constraints from the primitive itself.

            self.logger.debug("finding addl constraints for %s using ns %s" %
                              (solution['primitive']['name'],
                               solution['ns']))

            # new_constraints = self._get_additional_constraints(
            #     solution['primitive']['id'],
            #     solution['ns'])
            if proposed_plan is not None:
                new_constraints = []
            else:
                new_constraints = solution['discovered']
                solution.pop('discovered')

            # FIXME(rp)
            # pull in backends for primitives that can solve constraints
            # this should probably instead roll the consequence of the task
            # forward and re-run through satisifes constaraints
            if not solution['primitive']['id'] in self.task_primitives:
                be, prim_name = solution['primitive']['name'].split('.')
                if new_constraints is not None:
                    if prim_name != "add_backend":
                        new_expr = '"%s" in facts.backends' % be

                        if not new_expr in new_constraints:
                            new_constraints.append(new_expr)

                        self.logger.info(
                            ' - New constraints from primitive: %s' %
                            new_constraints)

            if proposed_plan is not None:
                new_constraints = []

            if new_constraints:
                new_constraints = [self.api.regularize_expression(x)
                                   for x in new_constraints]

                # FIXME(rp): we should be carrying constraints and
                # consequences around as sets rather than lists anyway
                new_constraints = [x for x in list(set(new_constraints))
                                   if not self._constraint_satisfied(x)]

            new_solver = None

            if new_constraints is None:
                self.logger.info(' - abandoning solution %s -- unsolvable' %
                                 solution['primitive']['name'])
            else:
                # find the concrete consequence so we can roll forward
                # the cluster api representation

                # these should really be the consequences of the primitive.
                consequences = solution['primitive']['consequences']

                self.logger.info(' - old constraints: %s' % constraints)

                for consequence in consequences:
                    concrete_consequence = ast.concrete_expression(
                        consequence, solution['ns'])
                    applied_consequences.append(concrete_consequence)
                    concrete_constraints = ast.invert_expression(
                        concrete_consequence)
                    self.logger.info(
                        'Adding consequence %s, solving constraints %s' %
                        (concrete_consequence, concrete_constraints))

                    # for concrete_constraint in concrete_constraints:
                    #     if concrete_constraint in constraints:
                    #         constraints.remove(concrete_constraint)

                if solution['solves'] in constraints:
                    constraints.remove(solution['solves'])

                # consequence = solution['consequence']
                # if consequence:
                #     concrete_consequence = ast.concrete_expression(
                #         consequence, solution['ns'])
                #     applied_consequences.append(concrete_consequence)
                #     constraints.remove(solution['solves'])

                self.logger.info(' - Implementing as new solve step: %s' %
                                 constraints)
                new_solver = Solver(self.base_api, self.node_id,
                                    constraints + new_constraints, self,
                                    solution['primitive'], ns=solution['ns'],
                                    applied_consequences=applied_consequences)

                self.children.append(new_solver)
                if new_solver.constraints == []:
                    return new_solver

        return None

    def print_tree(self, level=0):
        if self.prim:
            self.logger.info('%sPrim: %s' % (
                '  ' * level, self.prim['name']))
            self.logger.info('%sNS: %s' % (
                '  ' * level, self.ns))
            self.logger.info('%sConstraints: %s' % (
                '  ' * level, self.constraints))
            self.logger.info('%sApplied consequences: %s' % (
                '  ' * level, self.applied_consequences))
        else:
            self.logger.info('ROOT NODE')
            self.logger.info('Constraints: %s' % self.constraints)

        self.logger.info('%s (with %d children)' % (
            '  ' * level, len(self.children)))

        for child in self.children:
            child.print_tree(level + 1)

    def found_solution(self):
        if len(self.constraints) == 0:
            return True

        # for child in self.children:
        #     if child.found_solution():
        #         return True

        return False

    def solve(self):
        """
        Try to solve a set of constraints.  This sets up the
        initial constraint set, then splays all the possible
        primitives that move us close to solution.  Then it
        walks through all those in series to bring another
        solution generation, so on until one of the solution
        plans is successful, or there are no more primitives
        to consider moving us toward the goal.

        It returns (is_solvable, requires_input, plan), where
        solvable is the ability to solve the plan without any
        input, requires_input describes the ability to solve
        the plan if given some additional input, and plan is
        the considered solve plan
        """

        top_level = self
        current_leaves = [self]
        solution_node = None

        while(len(current_leaves) > 0 and not solution_node):
            new_leaves = []

            for leaf in current_leaves:
                solution_node = leaf.solve_one()
                # yeild to gevent
                gevent.sleep(0)
                if solution_node:
                    break

                # otherwise, we update our leaves and run
                # for solutions on leaves
                #
                # we'll have a bunch of single-level leaves,
                # or a single-path solution
                for child in leaf.children:
                    new_child = child

                    while len(new_child.children) > 0:
                        new_child = new_child.children[0]

                    new_leaves.append(new_child)
                    if new_child.found_solution():
                        solution_node = new_child

                # new_leaves = new_leaves + leaf.children

            if not solution_node:
                current_leaves = new_leaves
                top_level.print_tree()

        if solution_node:
            self.logger.debug('BEFORE BACKPRUNING')
            top_level.print_tree()

            while solution_node.parent:
                # backprune the solution
                solution_node.parent.children = [solution_node]
                solution_node = solution_node.parent

            # solution_node is now the root.
            # now we need to solve for args...
            plan = solution_node.plan()
            self.logger.debug("PLAN IS: %s" % plan)

            plan_solvable = True
            plan_choosable = False

            for step in plan:
                self.logger.debug('Solving args for step: %s' % step)
                prim = self._get_primitive_by_name(step['primitive'])
                if prim is None:
                    raise ValueError('cannot find prim in proposed plan. doh!')

                # terribleness below -- add in the task args if it is runtask
                #
                # this should really solve itself as a consequence of having
                # strong type knowledge, but as we have no strong knowledge
                # (or even weak type knowledge) we have to stuff this in
                # manually.  FIXME(rp): revisit this when we have types
                #
                # this should probably go away.

                addl_args = {}

                if prim['name'] == 'agent.run_task':
                    task_name = step['ns']['action']
                    task = [x for x in self.task_primitives.values()
                            if x['task_name'] == task_name]
                    if len(task) == 1:
                        addl_args = task[0]['args']

                self.logger.debug('discovered additional args: %s' % addl_args)

                addl_args.update(prim['args'])

                self.logger.debug('total args: %s' % addl_args)

                eval_args = dict([[x, addl_args[x]] for x in addl_args if
                                  addl_args[x]['type'] == 'evaluated'])
                other_args = dict([[x, addl_args[x]] for x in addl_args if
                                   addl_args[x]['type'] != 'evaluated'])

                for arg in other_args:
                    # walk through and see if we can solve this.
                    # man, this is stupid ugly
                    solvable, msg, choices = self.solve_arg(arg,
                                                            addl_args[arg],
                                                            step['ns'])
                    argv = addl_args[arg]
                    if solvable:
                        step['ns'][arg] = choices
                    elif choices:
                        plan_choosable = True
                        if(argv['required']):
                            plan_solvable = False
                        if not 'args' in step:
                            step['args'] = {}
                        step['args'][arg] = argv
                        step['args'][arg]['options'] = choices
                        step['args'][arg]['message'] = msg
                    else:
                        plan_choosable = True
                        if argv['required'] is True:
                            plan_solvable = False

                        if not 'args' in step:
                            step['args'] = {}
                        step['args'][arg] = argv
                        step['args'][arg]['message'] = msg

                if plan_solvable:
                    # express the evaluated args
                    eval_ns = {}
                    for k, v in step['ns'].items():
                        eval_ns[k] = v

                    node = self.base_api._model_get_by_id('nodes',
                                                          self.node_id)
                    nodes = self.base_api._model_get_all('nodes')

                    eval_ns['self'] = node
                    eval_ns['nodes'] = dict([(str(x['id']), x) for x in nodes])

                    # we've poked all the solved args into the ns,
                    # now, let's express them
                    for arg, val in eval_args.items():
                        if arg not in step['ns']:
                            self.logger.debug('expressing %s' %
                                              val['expression'])

                            # really, some of these should get bound at
                            # adventureate time... this is kind of wrong
                            step['ns'][arg] = \
                                opencenter.webapp.ast.apply_expression(
                                    eval_ns, val['expression'], self.base_api)

            self.logger.debug('returning (%s, %s, %s)' % (plan_solvable,
                                                          plan_choosable,
                                                          plan))
            return plan_solvable, plan_choosable, plan
        else:
            return False, False, []

    def plan(self):
        current = []
        if self.prim:
            current.append({'primitive': self.prim['name'],
                            'ns': self.ns,
                            'weight': self.prim['weight'],
                            'timeout': self.prim['timeout']})

        if len(self.children) > 1:
            raise ValueError('solution tree not pruned')

        if len(self.children) == 1:
            current += self.children[0].plan()

        current_sorted = sorted(current, key=lambda x: x['weight'],
                                reverse=True)

        if self.parent is None:
            return [{'primitive': x['primitive'],
                     'timeout': x['timeout'],
                     'ns': x['ns']} for x in current_sorted]
        return current_sorted

    def adventure(self, state_number=0):
        if self.prim:
            if len(self.children) > 1:
                raise ValueError('solution tree not pruned')

            state = 's%d' % state_number
            next_state = 's%d' % (state_number + 1)

            adventure = {
                's%d' % state_number: {
                    'primitive': self.prim['name'],
                    'parameters': self.ns
                }
            }

            if len(self.children) == 1:
                adventure[state]['on_success'] = next_state
                adventure.update(self.children[0].adventure(state_number + 1))

            return adventure
        else:
            return {'start_state': 's0',
                    'states': self.children[0].adventure()}

    def dotty(self, fd):
        if self.parent is None:
            print >>fd, 'digraph G {\n'

        print >>fd, '"%s" [shape=record, label="{%s|{Namespace|%s}' \
            '|{Constraints|%s}}"]' % (
            id(self), self.prim['name'] if self.prim else 'ROOT',
            '\\n'.join(['%s = %s' % (
                        x, self.ns[x]) for x in self.ns]).replace('"', '\\"'),
            '\\n'.join(['%s' % (
                        x,) for x in self.constraints]).replace('"', '\\"'))
        for child in self.children:
            print >>fd, '"%s" -> "%s"' % (id(self), id(child))
            child.dotty(fd)

        if self.parent is None:
            print >>fd, '}\n'

    # solves any args not necessary for meeting constraints,
    # but otherwise required (or optional)
    #
    # returns (solvable, msg, choices | selected choice)
    #
    # so... (False, "Cannot find interface 'chef-server'", None)
    # or... (False, "Choose interface 'chef-server'", [2,3])
    # or... (True, None, 2)
    #
    # It is up to the caller to decide whether unsolvability
    # of these args is a fatal or non-fatal condition
    #
    def solve_arg(self, name, arg, ns):
        if name in ns:
            return (True, None, ns[name])

        if arg['type'] == 'interface':
            iname = arg['name']
            int_query = 'filter_type="interface" and name="%s"' % iname
            iface = self.api._model_query('filters', int_query)
            if len(iface) == 0:
                return (False, 'unknown interface "%s"' % iname, None)

            if len(iface) > 1:
                return (False, 'multiple definitions of iface "%s"' % iname,
                        None)

            iface_query = iface[0]['full_expr']
            nodes = self.api._model_query('nodes', iface_query)

            if len(nodes) == 0:
                return (False, 'unsatisifed interface "%s"' % iname, None)

            if len(nodes) == 1:
                return (True, None, nodes[0]['id'])

            return (False, 'Multiple interfaces for "%s"' % arg['name'],
                    [x['id'] for x in nodes])

        return (False, 'I cannot solve for type "%s"' % arg['type'], None)
