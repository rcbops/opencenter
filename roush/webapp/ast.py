#!/usr/bin/env python

import logging
import re


# some common utility functions
def util_nth(n, ary):
    if not isinstance(ary, list):
        return None

    if not isinstance(n, int):
        return None

    if (len(ary) - 1) < n:
        return None

    return ary[n]


def util_str(what):
    if not what:
        return None

    return str(what)


def util_int(what):
    if not what:
        return None

    return int(what)


def util_max(ary):
    if not isinstance(ary, list):
        return False
    return max(ary)


def util_count(ary):
    if not isinstance(ary, list):
        return None
    return len(ary)


def util_union(listish1, listish2):
    # I'm not entirely sure how this should work.. this is
    # likely not a very useful implementation
    newlist = None

    if listish1 is None:
        listish1 = []

    if isinstance(listish1, list):
        if isinstance(listish2, list):
            newlist = listish1 + [x for x in listish2 if x not in listish1]
        else:
            newlist = listish1
            if not listish2 in newlist:
                newlist.append(listish2)

    return newlist


def util_filter(node_type, input_filter):
    builder = FilterBuilder(FilterTokenizer(), "%s: %s" % (node_type,
                                                           input_filter))

    result = builder.eval()
    return result


def util_printf(fmt, *args):
    try:
        return fmt % args
    except Exception:
        return None

default_functions = {'nth': util_nth,
                     'str': util_str,
                     'int': util_int,
                     'max': util_max,
                     'filter': util_filter,
                     'count': util_count,
                     'printf': util_printf,
                     'union': util_union}


class AbstractTokenizer(object):
    def __init__(self):
        self.tokens = []
        self.remainer = ''
        self.logger = logging.getLogger('filter.tokenizer')

    def parse(self, input_expression):
        self.tokens, self.remainder = self.scanner.scan(input_expression)
        self.tokens.append(('EOF', None))

        if self.remainder != '':
            raise RuntimeError(
                'Cannot parse.  Input: %s\nTokens: %s\nRemainder %s' %
                (input_expression, self.tokens, self.remainder))

        self.logger.debug('Tokenized %s as %s' %
                          (input_expression, self.tokens))
        return True

    def scan(self):
        self.logger.debug('popping token %s' % str(self.peek()))
        return self.tokens.pop(0)

    def peek(self):
        return self.tokens[0]


class ExpressionTokenizer(AbstractTokenizer):
    def __init__(self):
        super(ExpressionTokenizer, self).__init__()

        self.scanner = re.Scanner([
            (r":=", self.assignment_op),
            (r"[ \t\n]+", None),
            (r"[0-9]+", self.number),
            (r"none", self.none),
            (r"true", self.bool_op),
            (r"false", self.bool_op),
            (r",", self.comma),
            (r"\(", self.open_paren),
            (r"\)", self.close_paren),
            (r"'([^'\\]*(?:\\.[^'\\]*)*)'", self.qstring),
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', self.qstring),
            (r"[A-Za-z_\.]*", self.identifier),
        ])

    # token generators
    def assignment_op(self, scanner, token):
        return 'OP', token

    def number(self, scanner, token):
        return 'NUMBER', token

    def identifier(self, scanner, token):
        return 'IDENTIFIER', token

    def bool_op(self, scanner, token):
        return 'BOOL', token.upper()

    def qstring(self, scanner, token):
        whatquote = token[0]
        otherquote = '\\"'
        if whatquote == '"':
            otherquote = "\\'"

        return 'STRING', token[1:-1].replace(otherquote, whatquote)

    def open_paren(self, scanner, token):
        return 'OPENPAREN', token

    def close_paren(self, scanner, token):
        return 'CLOSEPAREN', token

    def comma(self, scanner, token):
        return 'COMMA', token

    def none(self, scanner, token):
        return 'NONE', token


# Stupid tokenizer.  Use:
#
# ft.parse(filter)
# ft.scan() returns (token,value) tuple, destroying token
# ft.peek() returns (token,value) tuple, leaving token on stack.
#           if you peek and decide to process the token, then
#           make sure you eat the token with a scan()!
#
# Since the entire filter is pre-tokenized, one could add
# arbitrary lookahead.  I don't need it tho.
#
# it's trivially easy to confuse this lexer.
#
class FilterTokenizer(AbstractTokenizer):
    def __init__(self):
        super(FilterTokenizer, self).__init__()

        self.scanner = re.Scanner([
            (r"!", self.negation),
            (r"or", self.or_op),
            (r"and", self.and_op),
            (r"none", self.none),
            (r"in ", self.in_op),
            (r"true", self.bool_op),
            (r"false", self.bool_op),
            (r",", self.comma),
            (r"[ \t\n]+", None),
            (r"[0-9]+", self.number),
            (r"\(", self.open_paren),
            (r"\)", self.close_paren),
            (r"'([^'\\]*(?:\\.[^'\\]*)*)'", self.qstring),
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', self.qstring),
            (r"[a-zA-Z_]*:", self.typedef),
            (r"\<\=|\>\=", self.op),
            (r"\=|\<|\>", self.op),
            (r"[A-Za-z_\.]*", self.identifier),
        ])

    # token generators
    def typedef(self, scanner, token):
        return 'TYPEDEF', token[0:-1]

    def op(self, scanner, token):
        return 'OP', token

    def number(self, scanner, token):
        return 'NUMBER', token

    def negation(self, scanner, token):
        return 'UNEG', token

    def identifier(self, scanner, token):
        return 'IDENTIFIER', token

    def bool_op(self, scanner, token):
        return 'BOOL', token.upper()

    def qstring(self, scanner, token):
        whatquote = token[0]
        otherquote = '\\"'
        if whatquote == '"':
            otherquote = "\\'"

        return 'STRING', token[1:-1].replace(otherquote, whatquote)

    def open_paren(self, scanner, token):
        return 'OPENPAREN', token

    def close_paren(self, scanner, token):
        return 'CLOSEPAREN', token

    def or_op(self, scanner, token):
        return 'OR', token

    def and_op(self, scanner, token):
        return 'AND', token

    def in_op(self, scanner, token):
        return 'OP', 'IN'

    def comma(self, scanner, token):
        return 'COMMA', token

    def none(self, scanner, token):
        return 'NONE', token


class AstBuilder(object):
    def __init__(self, tokenizer, input_expression, functions={}):
        self.tokenizer = tokenizer
        self.input_expression = input_expression
        self.logger = logging.getLogger(__name__)
        self.logger.debug('New builder on expression: %s' %
                          self.input_expression)
        self.functions = functions

    def build(self):
        self.tokenizer.parse(self.input_expression)
        root_node = self.parse()
        return root_node

    def eval(self):
        raise NotImplementedError('eval not implemented')

    def parse(self):
        raise NotImplementedError('parse not implemented')


# these are small expressions.  :)
# expression -> evalable_item | evalable_item op evalable_item
# evalable_item -> function(evalable_item[, e_i [, ...]]) | identifier | value
class ExpressionBuilder(AstBuilder):
    def __init__(self, tokenizer, input_expression,
                 input_type=None, functions={}):
        super(ExpressionBuilder, self).__init__(tokenizer, input_expression,
                                                functions=functions)
        self.input_type = input_type

    def parse(self):
        return self.parse_expression()

    def parse_expression(self):
        self.logger.debug('parsing expression')

        lhs = self.parse_evaluable_item()
        self.logger.debug('lhs: %s' % lhs)

        token, val = self.tokenizer.scan()
        if token == 'EOF':
            return lhs

        if token != 'OP':
            raise SyntaxError('Expecting op token')

        op = val
        self.logger.debug('op: %s' % op)

        rhs = self.parse_evaluable_item()
        self.logger.debug('rhs: %s' % rhs)

        return Node(lhs, op, rhs)

    def parse_evaluable_item(self):
        token, val = self.tokenizer.scan()

        if token == 'NUMBER':
            return Node(int(val), 'NUMBER', None)

        if token == 'STRING':
            return Node(str(val), 'STRING', None)

        if token == 'BOOL':
            return Node(val, 'BOOL', None)

        if token == 'NONE':
            return Node(None, 'NONE', None)

        if token == 'IDENTIFIER':
            next_token, next_val = self.tokenizer.peek()
            if next_token != 'OPENPAREN':
                return Node(str(val), 'IDENTIFIER', None)
            else:
                self.tokenizer.scan()  # eat the paren

                done = False
                args = []
                function_name = str(val)

                while not done:
                    args.append(self.parse_evaluable_item())

                    token, val = self.tokenizer.scan()

                    if token == 'CLOSEPAREN':
                        # done parsing evaluable item
                        return Node(function_name, 'FUNCTION', args)

                    if token != 'COMMA':
                        raise RuntimeError('expecting comma or close paren')

        raise RuntimeError('expecting evaluable item')


#
# This is a pretty trivial implementation.  The production
# rules are as follows:
#
# phrase -> {typedef}? andexpr EOF
# andexpr -> orexpr { T_AND orexpr }
# orexpr -> expr { T_OR expr }
# expr -> T_OPENPAREN andexpr T_CLOSEPAREN | criterion
# criterion -> evaluable_item [ { uneg } op evaluable_item ]
# evalable_item -> function(evaluable_item, e_i, ...) | identifier | value
#
# field -> datatype.value
# op -> '=', '<', '>'
# value -> number | string
#
# Lots of small problems here.. nodes should probably
# store both tokens and
class FilterBuilder(AstBuilder):
    def __init__(self, tokenizer, input_expression,
                 input_type=None, functions=default_functions):
        super(FilterBuilder, self).__init__(tokenizer, input_expression,
                                            functions=functions)
        self.input_type = input_type

    def parse(self):
        return self.parse_phrase()

    def eval(self):
        # avoid some circular includes
        import roush.db.api as api

        # get a list of all the self.input_types, and eval each in turn
        root_node = self.build()

        if not self.input_type:
            raise SyntaxError('unknown filter type')

        nodes = api._model_get_all(self.input_type)

        result = []

        for node in nodes:
            logging.debug('Checking node %s' % node['id'])
            if root_node.eval_node(node, self.functions):
                result.append(node)

        logging.debug("Found %d results" % len(result))

        return result

    # criterion -> evaluable_item { uneg } op evaluable_item
    def parse_criterion(self):
        negate = False

        lhs = self.parse_evaluable_item()

        token, val = self.tokenizer.peek()

        if token == 'UNEG' or token == 'OP':
            token, val = self.tokenizer.scan()

            if token == 'UNEG':
                negate = True
                token, val = self.tokenizer.scan()

            if token != 'OP':
                raise SyntaxError('Expecting {UNEG} BOOL | OP')

            op = val
            rhs = self.parse_evaluable_item()
            return Node(lhs, op, rhs, negate)
        else:
            return lhs

    # evaulable_item -> function(evalable_item, ...) | identifier | value
    def parse_evaluable_item(self):
        token, val = self.tokenizer.scan()

        if token == 'NUMBER':
            return Node(int(val), 'NUMBER', None)

        if token == 'STRING':
            return Node(str(val), 'STRING', None)

        if token == 'BOOL':
            return Node(val, 'BOOL', None)

        if token == 'NONE':
            return Node(None, 'NONE', None)

        if token == 'IDENTIFIER':
            next_token, next_val = self.tokenizer.peek()
            if next_token != 'OPENPAREN':
                return Node(str(val), 'IDENTIFIER', None)
            else:
                self.tokenizer.scan()  # eat the paren

                done = False
                args = []
                function_name = str(val)

                while not done:
                    args.append(self.parse_evaluable_item())

                    token, val = self.tokenizer.scan()

                    if token == 'CLOSEPAREN':
                        # done parsing evaluable item
                        return Node(function_name, 'FUNCTION', args)

                    if token != 'COMMA':
                        raise SyntaxError('expecting comma or close paren')

        raise SyntaxError('expecting evaluable item')

    # expr -> T_OPENPAREN andexpr T_CLOSEPAREN | criterion
    def parse_expr(self):
        token, val = self.tokenizer.peek()

        if token == 'OPENPAREN':
            self.tokenizer.scan()
            node = self.parse_andexpr()
            token, val = self.tokenizer.scan()
            if token != 'CLOSEPAREN':
                raise SyntaxError('expecting close paren')
            return node
        else:
            return self.parse_criterion()

    # orexpr -> expr { T_OR expr }
    def parse_orexpr(self):
        node = self.parse_expr()

        token, val = self.tokenizer.peek()
        if token == 'OR':
            self.tokenizer.scan()  # eat the token
            rhs = self.parse_andexpr()
            return Node(node, 'OR', rhs)
        else:
            return node

    # andexpr -> orexpr { T_AND orexpr }
    def parse_andexpr(self):
        node = self.parse_orexpr()

        token, val = self.tokenizer.peek()
        if token == 'AND':
            self.tokenizer.scan()  # eat the token
            rhs = self.parse_andexpr()
            return Node(node, 'AND', rhs)
        else:
            return node

    # phrase -> {typedef}? andexpr EOF
    def parse_phrase(self):
        token, val = self.tokenizer.peek()

        if token == 'TYPEDEF':
            self.input_type = val
            self.tokenizer.scan()

        node = self.parse_andexpr()

        token, val = self.tokenizer.scan()
        if token != 'EOF':
            raise SyntaxError('expecting EOF')

        return node


class Node:
    def __init__(self, lhs, op, rhs, negate=False):
        self.lhs = lhs
        self.rhs = rhs
        self.op = op
        self.negate = negate
        self.logger = logging.getLogger('filter.node')

    def value_to_s(self):
        if self.op == 'STRING':
            return "'%s'" % self.lhs.replace("'", "\'")

        return str(self.lhs)

    def to_s(self):
        if self.op in ['NUMBER', 'BOOL', 'STRING',
                       'IDENTIFIER', 'NONE']:
            return self.value_to_s()

        if self.op == 'FUNCTION':
            return '%s(%s)' % (self.lhs, ', '. join(map(lambda x: x.to_s(),
                                                        self.rhs)))

        if self.op == 'AND' or self.op == 'OR':
            return '(%s) %s (%s)' % (self.lhs.to_s(), self.op, self.rhs.to_s())

        return '%s %s%s %s' % (self.lhs.to_s(), '!' if self.negate else '',
                               self.op, self.rhs.to_s())

    def invert(self):
        # this is kind of strange, as it only inverts things it can invert,
        # and isn't really complete.  It relies on the kindness of strangers.
        if self.op == 'AND':
            return self.lhs.invert() + self.rhs.invert()

        if self.op == '=':
            return ['%s := %s' % (self.lhs.value_to_s(),
                                  self.rhs.value_to_s())]
        if self.op == 'IN':
            return ['%s := union(%s, %s)' % (self.rhs.value_to_s(),
                                             self.rhs.value_to_s(),
                                             self.lhs.value_to_s())]

        raise SyntaxError('un-invertable operator: %s' % self.op)

    def dotty(self, fd):
        self.logger.debug("Dottying: %s %s %s" % (self.lhs, self.op, self.rhs))

        lhs_id = 'x'
        rhs_id = 'x'

        if self.op in ['NUMBER', 'BOOL', 'STRING', 'IDENTIFIER', 'NONE']:
            label = self.lhs
            if self.op == 'STRING':
                label = "'" + label + "'"

            fd.write('"%s" [label = "%s"]' % (id(self), label) + ';\n')
        elif self.op == 'FUNCTION':
            fd.write('"%s" [label = "%s()"]' % (id(self), self.lhs) + ';\n')
            arg = 0
            for d in self.rhs:
                arg += 1
                d.dotty(fd)
                fd.write('"%s" -> "%s" [label="arg%d"]' %
                         (id(self), id(d), arg) + ';\n')
        else:
            fd.write('"%s" [label="%s"]' % (str(id(self)),
                                            str(self.op)) + ';\n')
            self.lhs.dotty(fd)
            self.rhs.dotty(fd)
            fd.write('"%s" -> "%s"' % (id(self), id(self.lhs)) + ';\n')
            fd.write('"%s" -> "%s"' % (id(self), id(self.rhs)) + ';\n')

    def eval_identifier(self, node, identifier):
        import roush.db.api as api

        self.logger.debug('resolving identifier "%s" on:\n%s' %
                          (identifier, node))

        if not identifier:
            return None

        if identifier.find('.') == -1:
            if identifier in node:
                return node[identifier]
            else:
                # should this raise?
                self.logger.debug('cannot find attribute %s in node' %
                                  identifier)
                return None

        # of the format something.something
        (attr, rest) = identifier.split('.', 1)

        self.logger.debug('checking for attr %s in %s' % (attr, node))

        if attr in node:
            return self.eval_identifier(node[attr], rest)
        else:
            self.logger.debug('no attr... try %s in link %s' % (rest, attr))

            if "%s%s" % (attr, '_id') in node:
                the_id = node["%s%s" % (attr, '_id')]
                if the_id:
                    self.logger.debug('found link type %s with id: %s' %
                                      (attr, str(the_id)))
                    try:
                        # grab the linked object...
                        new_node = api._model_get_by_id("%ss" % attr, the_id)
                        self.logger.debug("Indirected object: %s" % new_node)
                    except Exception as e:
                        self.logger.debug('cannot lookup the object type: %s' %
                                          str(e))
                        return None

                    return self.eval_identifier(new_node, rest)

        return None

    def __str__(self):
        if self.op == 'STRING':
            return str(self.lhs)

        if self.op == 'NUMBER':
            return str(int(self.lhs))

        if self.op == 'BOOL':
            return str(self.lhs)

        if self.op == 'IDENTIFIER':
            return 'IDENTIFIER %s' % self.lhs

        if self.op == 'NONE':
            return 'VALUE None'

        if self.op == 'FUNCTION':
            return 'FN %s(%s)' % (str(self.lhs), ', '.join(map(str, self.rhs)))

        return '(%s) %s (%s)' % (str(self.lhs), self.op, str(self.rhs))

    def eval_node(self, node, functions):
        rhs_val = None
        lhs_val = None
        result = False

        retval = None

        self.logger.debug('evaluating %s' % str(self))

        if self.op in ['STRING', 'NUMBER', 'BOOL',
                       'IDENTIFIER', 'FUNCTION', 'NONE']:
            if self.op == 'STRING':
                retval = str(self.lhs)

            if self.op == 'NUMBER':
                retval = int(self.lhs)

            if self.op == 'BOOL':
                if self.lhs == 'TRUE':
                    retval = True
                else:
                    retval = False

            if self.op == 'IDENTIFIER':
                retval = self.eval_identifier(node, self.lhs)

            if self.op == 'NONE':
                retval = None

            if self.op == 'FUNCTION':
                if not self.lhs in functions:
                    raise SyntaxError('unknown function %s' % self.lhs)

                args = map(lambda x: x.eval_node(node, functions), self.rhs)
                retval = functions[self.lhs](*args)

            self.logger.debug('evaluated %s to %s' % (str(self), retval))
            return retval

        self.logger.debug('arithmetic op, type %s' % self.op)

        # otherwise arithmetic op
        lhs_val = self.lhs.eval_node(node, functions)
        rhs_val = self.rhs.eval_node(node, functions)

        # wrong types is always false
        if type(lhs_val) == unicode:
            lhs_val = str(lhs_val)

        if type(rhs_val) == unicode:
            rhs_val = str(rhs_val)

        self.logger.debug('checking %s %s %s' % (lhs_val, self.op, rhs_val))

        if self.op == '=':
            if lhs_val == rhs_val:
                result = True
        elif self.op == '<':
            if type(lhs_val) != type(rhs_val):
                return False
            elif lhs_val < rhs_val:
                result = True
        elif self.op == '>':
            if type(lhs_val) != type(rhs_val):
                return False
            elif lhs_val > rhs_val:
                result = True
        elif self.op == '<=':
            if type(lhs_val) != type(rhs_val):
                return False
            elif lhs_val <= rhs_val:
                result = True
        elif self.op == '>=':
            if type(lhs_val) != type(rhs_val):
                return False
            elif lhs_val >= rhs_val:
                result = True
        elif self.op == 'AND':
            result = lhs_val and rhs_val
        elif self.op == 'OR':
            result = lhs_val or rhs_val
        elif self.op == 'IN':
            try:
                if lhs_val in rhs_val:
                    result = True
            except Exception:
                result = False
        else:
            raise SyntaxError('bad op token (%s)' % self.op)

        if self.negate:
            return not result

        return result


class Solver:
    def __init__(self, node, cluster, constraints):
        self.constraints = constraints
        self.node = node
        self.consequences = []
        self.children = []
        self.logger = logging.getLogger('%s.solver' % __name__)

    def solve(self):
        import roush.db.api as api
        # walk through all the primitives, and see what primitives
        # have constraints that are met, and spin off a new solver
        # from that state.
        primitives = api._model_get_all('primitives')

        applied_primitives = []

        for primitive in primitives:
            self.logger.debug('evaluating primitive %s' % primitive['name'])
            can_add = True
            if primitive['constraints'] != []:
                constraint_filter = ' AND '.join(map(lambda x: '(%s)' % x,
                                                     primitive.constraints))
                builder = FilterBuilder(FilterTokenizer, constraint_filter,
                                        'nodes')
                root_node = builder.build()

                can_add = root_node.eval_node(self.node)

            self.logger.debug('primitive "%s" meets constraints: %s' %
                              (primitive['name'], can_add))
            if can_add:
                applied_primitives.append(primitive)

        # now we have a list of primitives that can be applied, so
        # nail down the arguments and apply the primitives
