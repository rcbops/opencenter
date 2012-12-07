#!/usr/bin/env python

import copy
import logging
import re

import roush.backends
from roush.webapp import ast
from roush.db import api as db_api


class Solver:
    def __init__(self, api, node_id, constraints,
                 parent=None, prim=None, ns={}, applied_consequences=[]):

        self.constraints = constraints
        self.node_id = node_id
        self.base_api = api
        self.consequences = []
        self.applied_consequences = applied_consequences
        self.children = []
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.parent = parent
        self.prim = prim
        self.ns = ns

        # roll the applied consequences forward in an ephemeral
        # api, and do our resolution from that.
        self.api = db_api.ephemeral_api_from_api(self.base_api)
        pre_node = self.api._model_get_by_id('nodes', self.node_id)

        for consequence in self.applied_consequences:
            ephemeral_node = self.api._model_get_by_id('nodes', self.node_id)
            ast.apply_expression(ephemeral_node, consequence, self.api)

        self.logger.debug('Node before applying consequences: %s' %
                          pre_node)
        self.logger.debug('Applied consequences: %s' %
                          self.applied_consequences)
        ephemeral_node = self.api._model_get_by_id('nodes', self.node_id)
        self.logger.debug('Node after applying consequences: %s' %
                          ephemeral_node)

    @classmethod
    def from_plan(cls, api, node_id, constraints, plan):
        root_solver = Solver(api, node_id, constraints)
        current_node = root_solver

        for plan_item in plan:
            current_node.solve_one(plan_item)
            if len(current_node.children) != 1:
                raise ValueError("Couldn't apply plan")

            current_node = current_node.children[0]

        if len(current_node.children) != 0:
            raise ValueError("Plan didn't satisfy constraints")

        return root_solver

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
        can_add = True

        if primitive['constraints'] != []:
            constraint_filter = ' AND '.join(map(lambda x: '(%s)' % x,
                                                 primitive['constraints']))

            can_add = self._constraint_satisfied(constraint_filter)
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

        if constraint_node.op not in ['IDENTIFIER', 'STRING']:
            self.logger.debug('Cannot coerce vars not IDENTIFIER or STRING')
            return False, {}

        if consequence_node.op not in ['IDENTIFIER', 'STRING']:
            self.logger.debug('Cannot coerce vars not IDENTIFIER or STRING')
            return False, {}

        if consequence_node.op != constraint_node.op:
            self.logger.debug('Cannot coerce dissimilar op types')
            return False, {}

        if consequence_node.lhs == constraint_node.lhs:
            self.logger.debug('Equal literals!  Success!')
            return True, {}

        match = re.match("(.*)\{(.*?)}(.*)", consequence_node.lhs)
        if match is None:
            self.logger.debug('dissimilar literals')
            return False, {}

        if not constraint_node.lhs.startswith(match.group(1)) or \
                not constraint_node.lhs.endswith(match.group(3)):
            self.logger.debug('cant coerce even with var binding')
            return False, {}

        key = match.group(2)
        value = constraint_node.lhs[len(match.group(1)):]
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

        return True, ns_lhs

    def _is_forwarding_solution(self, primitive, constraints, ns=None):
        """
        see if a primitive with a particular namespace binding
        can actually satisfy a constraint (mostly for plan
        testing)
        """

        potential = self._potential_solutions(primitive, constraints)
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

        return valid_solutions

    def solve_one(self, proposed_plan=None):
        """
        run a single pass of the solver, trying to find all the
        available primitives that can solve any existing constraint.
        """

        # first, build up asts of all my unsolved constraints
        constraint_list = self._build_constraints(self.constraints)

        # fix/regularize our internal constraint list
        self.constraints = [x['constraint'] for x in constraint_list]

        self.logger.debug('Solving for constraints: %s with plan: %s' %
                          (self.constraints, proposed_plan))

        # walk through all the primitives, and see what primitives
        # have constraints that are met, and spin off a new solver
        # from that state.

        primitives = []

        if proposed_plan:
            primitives = [self.api._model_get_by_id(
                'primitives',
                proposed_plan['primitive']['id'])]
        else:
            primitives = self.api._model_get_all('primitives')

        primitives = [x for x in primitives if self._can_meet_constraints(x)]

        # get all the primitives capable of being run, given the
        # primitive constraints

        # see if any of the appliable primitives have consequences that
        # could forward us to our goal.
        all_solutions = []

        if proposed_plan:
            plan_prim = proposed_plan['primitive']
            plan_ns = proposed_plan['args']

            primitive = self.api._model_get_by_id(
                'primitives',
                plan_prim['id'])

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
        self.logger.debug("Found %d solutions:" % len(all_solutions))
        for solution in all_solutions:
            self.logger.debug("%s with %s, solving %s" %
                              (solution['primitive']['name'],
                               solution['ns'],
                               solution['solves']))

            constraints = copy.deepcopy(self.constraints)
            applied_consequences = copy.deepcopy(self.applied_consequences)

            # if not solution['solves'] in constraints:
            #     raise RuntimeError('constraint disappeared?!?!')

            # get additional constraints from the primitive itself.
            new_constraints = roush.backends.additional_constraints(
                solution['primitive']['id'],
                solution['ns'])

            self.logger.debug('New constraints from primitive: %s' %
                              new_constraints)

            new_solver = None

            if new_constraints:
                new_constraints = [x for x in new_constraints if not
                                   self._constraint_satisfied(x)]

            if new_constraints and len(new_constraints) > 0:
                # do a subsolve on this
                subsolve = Solver(self.api, self.node_id, new_constraints)
                sub_success, _, sub_plan = subsolve.solve()
                if sub_success:
                    sub_solver = Solver.from_plan(
                        self.api, self.node_id,
                        new_constraints + constraints,
                        sub_plan)
                    new_solver = sub_solver.children[0]
            else:
                # find the concrete consequence so we can roll forward
                # the cluster api representation

                # these should really be the consequences of the primitive.
                consequences = solution['primitive']['consequences']

                for consequence in consequences:
                    concrete_consequence = ast.concrete_expression(
                        consequence, solution['ns'])
                    applied_consequences.append(concrete_consequence)
                    concrete_constraints = ast.invert_expression(
                        concrete_consequence)
                    self.logger.debug(
                        'Adding consequence %s, solving constraints %s' %
                        (concrete_consequence, concrete_constraints))

                    for concrete_constraint in concrete_constraints:
                        if concrete_constraint in constraints:
                            constraints.remove(concrete_constraint)

                # consequence = solution['consequence']
                # if consequence:
                #     concrete_consequence = ast.concrete_expression(
                #         consequence, solution['ns'])
                #     applied_consequences.append(concrete_consequence)
                #     constraints.remove(solution['solves'])

                new_solver = Solver(self.api, self.node_id,
                                    constraints, self,
                                    solution['primitive'], ns=solution['ns'],
                                    applied_consequences=applied_consequences)

            if new_solver:
                self.children.append(new_solver)

        for child in self.children:
            if child.found_solution():
                return child

        return None

    def print_tree(self, level=0):
        if self.prim:
            self.logger.debug('%sPrim: %s' % (
                '  ' * level, self.prim['name']))
            self.logger.debug('%sNS: %s' % (
                '  ' * level, self.ns))
            self.logger.debug('%sConstraints: %s' % (
                '  ' * level, self.constraints))
            self.logger.debug('%sApplied consequences: %s' % (
                '  ' * level, self.applied_consequences))
        else:
            self.logger.debug('ROOT NODE')

        self.logger.debug('%s (with %d children)' % (
            '  ' * level, len(self.children)))

        for child in self.children:
            child.print_tree(level + 1)

    def found_solution(self):
        return len(self.constraints) == 0

    def solve(self):
        top_level = self
        current_leaves = [self]
        solution_node = None

        while(len(current_leaves) > 0 and not solution_node):
            new_leaves = []

            for leaf in current_leaves:
                solution_node = leaf.solve_one()
                if solution_node:
                    break

                # otherwise, we update our leaves and run
                # for solutions on leaves
                #
                # we'll have a bunch of single-level leaves,
                # or a single-path solution
                for child in leaf.children:
                    while len(child.children) > 0:
                        child = child.children[0]
                    new_leaves.append(child)

                # new_leaves = new_leaves + leaf.children

            if not solution_node:
                current_leaves = new_leaves
                top_level.print_tree()

        if solution_node:
            while solution_node.parent:
                # backprune the solution
                solution_node.parent.children = [solution_node]
                solution_node = solution_node.parent

            # solution_node is now the root.
            return True, False, solution_node.plan()
        else:
            return False, False, []

    def plan(self):
        current = []
        if self.prim:
            current.append({'primitive': self.prim,
                            'args': self.ns,
                            'consequences': self.applied_consequences})

        if len(self.children) > 1:
            raise ValueError('solution tree not pruned')

        if len(self.children) == 1:
            current += self.children[0].plan()

        return current

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
    def solve_arg(self, name, arg, ns):
        if name in ns:
            return (True, ns[name])

        if arg['type'] == 'interface':
            iname = arg['name']
            int_query = 'filter_type="interface" and name="%s"' % iname
            iface = self.api._model_query('filters', int_query)
            if len(iface) == 0:
                return (False, 'unknown interface "%s"' % iname)

            if len(iface) > 1:
                return (False, 'multiple definitions of "%s"' % iname)

            iface_query = iface[0]['full_expr']
            nodes = self.api._model_query('nodes', iface_query)

            if len(nodes) == 0:
                return (False, 'unsatisifed interface "%s"' % iname)

            if len(nodes) == 1:
                return nodes[0]['id']

            return (False, 'Choice: %s' % ([x['id'] for x in nodes],))

        return (False, 'Somehow unknowable')
