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
        self.solutions = {}
        self.parent = parent
        self.prim = prim
        self.ns = ns

        # roll the applied consequences forward in an ephemeral
        # api, and do our resolution from that.
        self.api = db_api.ephemeral_api_from_api(self.base_api)
        pre_node = self.api._model_get_by_id('nodes', self.node_id)

        for consequence in self.applied_consequences:
            ephemeral_node = self.api._model_get_by_id('nodes', self.node_id)
            ast.apply_expression(ephemeral_node, consequence, api)

        self.logger.debug('Node before applying consequences: %s' %
                          pre_node)
        self.logger.debug('Applied consequences: %s' %
                          self.applied_consequences)
        ephemeral_node = self.api._model_get_by_id('nodes', self.node_id)
        self.logger.debug('Node after applying consequences: %s' %
                          ephemeral_node)

    def can_coerce(self, constraint_node, consequence_node):
        # see if the consequence expression can be forced
        # into the constraint form.

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

    def solve_one(self):
        # first, build up asts of all my unsolved constraints
        f_builder = ast.FilterBuilder(ast.FilterTokenizer())

        constraint_asts = []
        for constraint in self.constraints:
            self.logger.debug('ast-izing constraint %s' % constraint)
            f_builder.set_input(constraint)
            root_node = f_builder.build()
            constraint_asts.append({'constraint': constraint,
                                    'ast': root_node})

        expression_asts = []
        for constraint_struct in constraint_asts:
            for expression in constraint_struct['ast'].invert():
                self.logger.debug('ast-izing inv constraint %s' % expression)
                f_builder.set_input(expression)
                root_node = f_builder.build()
                expression_asts.append({'constraint':
                                        constraint_struct['constraint'],
                                        'ast': root_node})

        # walk through all the primitives, and see what primitives
        # have constraints that are met, and spin off a new solver
        # from that state.
        primitives = self.api._model_get_all('primitives')

        unmet_primitives = []
        applied_primitives = []

        for primitive in primitives:
            self.logger.debug('evaluating primitive for constraints: %s' %
                              primitive)
            can_add = True

            if primitive['constraints'] != []:
                constraint_filter = ' AND '.join(map(lambda x: '(%s)' % x,
                                                     primitive['constraints']))
                builder = ast.FilterBuilder(ast.FilterTokenizer(),
                                            constraint_filter,
                                            'nodes')
                root_node = builder.build()

                can_add = root_node.eval_node(self.node)
            self.logger.debug('primitive "%s" meets constraints: %s' %
                              (primitive['name'], can_add))
            if can_add:
                applied_primitives.append(primitive)
            else:
                unmet_primitives.append("%s: could not meet constraints" %
                                        primitive['name'])

        # see if any of the appliable primitives have consequences that
        # could forward us to our goal.
        bad_primitives = []

        for primitive in applied_primitives:
            self.logger.debug('checking forwardness of %s' % primitive['name'])

            can_satisfy = False
            ns = {}

            for constraint_struct in expression_asts:
                for consequence in primitive['consequences']:
                    prim_name = primitive['name']
                    prim_id = primitive['id']

                    f_builder.set_input(consequence)
                    consequence_ast = f_builder.build()

                    constraint_ast = constraint_struct['ast']
                    satisfaction, ns = self.can_solve(constraint_ast,
                                                      consequence_ast)

                    if satisfaction:
                        can_satisfy = True
                        self.solutions[prim_name] = {}
                        self.solutions[prim_name]['id'] = prim_id
                        self.solutions[prim_name]['prim'] = primitive
                        if not 'solved' in self.solutions[prim_name]:
                            self.solutions[prim_name]['solved'] = []

                        self.solutions[prim_name]['solved'].append(
                            constraint_struct['constraint'])

                        if not 'ns' in self.solutions[prim_name]:
                            self.solutions[prim_name]['ns'] = {}

                        for k, v in ns.items():
                            if k in self.solutions[prim_name]['ns']:
                                self.logger.error('### DUP BINDING ###')
                                raise RuntimeError('can this happen?')

                            self.solutions[prim_name]['ns'][k] = v

            if not can_satisfy:
                bad_primitives.append(primitive)
                unmet_primitives.append('%s: does not further goal' %
                                        primitive['name'])
            self.logger.debug('%s can forward: %s' % (primitive['name'],
                                                      can_satisfy))

        for primitive in bad_primitives:
            applied_primitives.remove(primitive)

        # now we have a list of primitives that can be applied, so
        # nail down the arguments and apply the primitives
        for name, solution in self.solutions.items():
            self.logger.debug('Solving args for %s' % solution)

            for arg, val in solution['prim']['args'].items():
                self.logger.debug('solving %s' % arg)
                solvable, result = self.solve_arg(
                    arg, val, solution['ns'])

                if solvable:
                    solution['ns'][arg] = result
                else:
                    pass

                self.logger.debug('Arg "%s" solvable: %s (%s)' % (
                    arg, solvable, result))

        self.logger.debug('unapplied_primitives: %s' %
                          ', '.join(unmet_primitives))

        self.logger.debug("Proposed paths forward:")
        for name in self.solutions:
            self.logger.debug(self.solutions[name])

        for name, solution in self.solutions.items():
            self.logger.debug('Met primitive "%s".  NS:' % name)

            for k, v in solution['ns'].items():
                self.logger.debug('  "%s" => "%s"' % (k, v))

            constraints = copy.deepcopy(self.constraints)
            applied_consequences = copy.deepcopy(self.applied_consequences)

            self.logger.debug('New consequences: %s' % solution['solved'])

            for solved in solution['solved']:
                if not solved in constraints:
                    raise RuntimeError('constraint disappeared!')

                consequence_list = ast.invert_expression(solved)
                for consequence in consequence_list:
                    self.logger.debug('adding applied consequence %s' %
                                      consequence)

                    applied_consequences.append(
                        ast.concrete_expression(consequence))
                constraints.remove(solved)

            # get additional constraints
            self.logger.debug('Getting additional constraints for %s' %
                              solution['prim']['id'])

            new_constraints = roush.backends.additional_constraints(
                solution['prim']['id'],
                solution['ns'])

            self.logger.debug('New constraints from primitive: %s' %
                              new_constraints)

            new_solver = Solver(self.base_api, self.node_id,
                                constraints + new_constraints, self,
                                solution['prim'], ns=solution['ns'],
                                applied_consequences=applied_consequences)

            self.children.append(new_solver)

        for child in self.children:
            if child.found_solution():
                return child

        return None

    def found_solution(self):
        return len(self.constraints) == 0

    def solve(self):
        current_leaves = [self]
        solution_node = None
        solution_track = []

        while(len(current_leaves) > 0 and not solution_node):
            new_leaves = []

            for leaf in current_leaves:
                solution_node = leaf.solve_one()
                if solution_node:
                    break

                # otherwise, we update our leaves and run
                # for solutions on leaves
                new_leaves = new_leaves + leaf.children

            if not solution_node:
                current_leaves = new_leaves

        if solution_node:
            while solution_node.parent:
                solution_track.insert(0, solution_node.plan())
                solution_node = solution_node.parent

                self.logger.debug('solution track: %s' % solution_track)

            return True, False, solution_track

        else:
            return False, False, solution_track

    def plan(self,):
        result_plan = {}
        result_plan['primitive'] = self.prim
        result_plan['args'] = self.ns
        result_plan['consequences'] = self.applied_consequences
        return result_plan

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
