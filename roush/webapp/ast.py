#!/usr/bin/env python

import copy
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

    result = builder.filter()
    return result


def util_ifcount(iface_name):
    import roush.db.api as api

    interface_query = 'filter_type="interface" and name="%s"' % iface_name
    filter_list = FilterBuilder(FilterTokenizer(), '%s: %s' %
                                ('filters', interface_query)).filter()

    if len(filter_list) != 1:
        raise SyntaxError('bad interface type %s' % iface_name)

    ifaces = api._model_query('nodes', filter_list[0]['full_expr'])
    return len(ifaces)


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
                     'union': util_union,
                     'ifcount': util_ifcount}


class AbstractTokenizer(object):
    def __init__(self):
        self.tokens = []
        self.remainer = ''
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))

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
            (r":=", self.op),
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
            (r"[A-Za-z_\.\-{}]*", self.identifier),
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
    def __init__(self, tokenizer, input_expression=None, functions={},
                 ns={}):
        self.tokenizer = tokenizer
        self.input_expression = input_expression
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.logger.debug('New builder on expression: %s' %
                          self.input_expression)
        self.functions = functions
        self.ns = ns

    def set_input(self, input_expression):
        self.logger.debug('resetting input expression to %s' %
                          input_expression)
        self.input_expression = input_expression

    def build(self):
        self.tokenizer.parse(self.input_expression)
        root_node = self.parse()
        return root_node

    def eval(self):
        raise NotImplementedError('eval not implemented')

    def parse(self):
        raise NotImplementedError('parse not implemented')


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
    def __init__(self, tokenizer, input_expression=None,
                 input_type=None, functions=default_functions,
                 ns={}):
        super(FilterBuilder, self).__init__(tokenizer, input_expression,
                                            functions=functions,
                                            ns=ns)
        self.input_type = input_type

    def parse(self):
        return self.parse_phrase()

    def filter(self, input_type=None):
        # avoid some circular includes
        import roush.db.api as api

        # get a list of all the self.input_types, and eval each in turn
        root_node = self.build()

        if input_type is None:
            self.logger.debug('unspecified input type, using %s' %
                              self.input_type)
            input_type = self.input_type

        if input_type is None:
            raise SyntaxError('unknown filter type')

        nodes = api._model_get_all(input_type)

        result = []

        for node in nodes:
            logging.debug('Checking node %s' % node['id'])
            if root_node.eval_node(node, self.functions, self.ns):
                result.append(node)

        logging.debug("Found %d results" % len(result))
        return result

    def eval_node(self, node, functions=None, symbol_table=None):
        root_node = self.build()

        if functions is None:
            functions = self.functions

        if symbol_table is None:
            symbol_table = self.symbol_table

        root_node.eval_node(node, functions=functions,
                            symbol_table=symbol_table)

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
            self.logger.debug('Set input type to %s' % self.input_type)

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
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))

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
            if (self.lhs.op in ['NUMBER',
                                'BOOL',
                                'STRING',
                                'IDENTIFIER',
                                'NONE'] and self.rhs.op == 'IDENTIFIER'):
                return ['%s := union(%s, %s)' % (self.rhs.value_to_s(),
                                                 self.rhs.value_to_s(),
                                                 self.lhs.value_to_s())]

        # foo.facts.blah := "blah"
        # foo.facts.blah := union(foo.facts, "blah")
        if self.op == ':=':
            if self.lhs.op == 'IDENTIFIER' and (self.rhs.op in ['NUMBER',
                                                                'BOOL',
                                                                'STRING',
                                                                'IDENTIFIER',
                                                                'NONE']):
                return ['%s = %s' % (self.lhs.value_to_s(),
                                     self.rhs.value_to_s())]
            if (self.lhs.op == 'IDENTIFIER' and (
                    self.rhs.op == 'FUNCTION' and (
                        self.rhs.lhs == 'union')) and (
                    self.lhs.lsh == self.rhs.rhs[0])):
                return ['%s IN %s' % (self.rhs.rhs[0].value_to_s(),
                                      self.rhs.rhs[1].value_to_s())]

        raise SyntaxError('un-invertable operator: %s' % self.op)

    def dotty(self, fd):
        self.logger.debug("Dottying: %s %s %s" % (self.lhs, self.op, self.rhs))

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

    def canonicalize_identifier(self, node, identifier, symbol_table={}):
        if not identifier:
            return None

        # check for string interpolation in identifier.
        match = re.match("(.*)\{(.*?)}(.*)", identifier)
        if match is not None:
            resolved_match_term = self.eval_identifier(node, match.group(2),
                                                       symbol_table)
            new_identifier = "%s%s%s" % (match.group(1), resolved_match_term,
                                         match.group(3))

            return self.canonicalize_identifier(node, new_identifier,
                                                symbol_table)

        return identifier

    def assign_identifier(self, node, identifier, value, symbol_table={}):
        # there are all kinds of places where this can go wrong.
        # we can create arbitrary facts, but not attributes, and here
        # we are just assuming that an expressed consequence is a valid
        # one.
        #
        # right now we'll assume that if this is expressed as a consequence,
        # it's actually realizable in the underlying data structure.  If not,
        # well... bad things.
        if not identifier:
            return None

        self.logger.debug('setting %s to %s' % (identifier, value))
        canonical = self.canonicalize_identifier(node, identifier,
                                                 symbol_table)

        self.logger.debug('canonicalized %s to %s' % (identifier, canonical))
        if canonical.find('.') == -1:
            node[canonical] = value
        else:
            (attr, rest) = canonical.split('.', 1)

            if attr not in node:
                node[attr] = {}

            self.assign_identifier(node[attr], rest, value,
                                   symbol_table)

    def eval_identifier(self, node, identifier, symbol_table={}):
        import roush.db.api as api

        self.logger.debug('resolving identifier "%s" on:\n%s with ns %s' %
                          (identifier, node, symbol_table))

        if node is None or identifier is None:
            raise TypeError('invalid node or identifier in eval_identifier')

        if identifier in symbol_table:
            return symbol_table[identifier]

        # check for string interpolation in identifier.
        match = re.match("(.*)\{(.*?)}(.*)", identifier)
        if match is not None:
            resolved_match_term = self.eval_identifier(node, match.group(2))
            new_identifier = "%s%s%s" % (match.group(1), resolved_match_term,
                                         match.group(3))

            return self.eval_identifier(node, new_identifier, symbol_table)

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
            return self.eval_identifier(node[attr], rest, symbol_table)
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

                    return self.eval_identifier(new_node, rest, symbol_table)

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

    def eval_node(self, node, functions=default_functions, symbol_table={}):
        rhs_val = None
        lhs_val = None
        result = False

        retval = None

        self.logger.debug('evaluating %s with symbol_table %s' %
                          (str(self), symbol_table))

        if self.op in ['STRING', 'NUMBER', 'BOOL',
                       'IDENTIFIER', 'FUNCTION', 'NONE']:
            if self.op == 'STRING':
                # check for string interpolation in identifier.
                retval = str(self.lhs)
                match = re.match("(.*)\{(.*?)}(.*)", retval)
                if match is not None:
                    resolved_match_term = self.eval_identifier(node,
                                                               match.group(2),
                                                               symbol_table)
                    retval = "%s%s%s" % (match.group(1), resolved_match_term,
                                         match.group(3))

            if self.op == 'NUMBER':
                retval = int(self.lhs)

            if self.op == 'BOOL':
                if self.lhs == 'TRUE':
                    retval = True
                else:
                    retval = False

            if self.op == 'IDENTIFIER':
                retval = self.eval_identifier(node, self.lhs, symbol_table)

            if self.op == 'NONE':
                retval = None

            if self.op == 'FUNCTION':
                if not self.lhs in functions:
                    raise SyntaxError('unknown function %s' % self.lhs)

                args = map(lambda x: x.eval_node(node,
                                                 functions, symbol_table),
                           self.rhs)

                retval = functions[self.lhs](*args)

            self.logger.debug('evaluated %s to %s' % (str(self), retval))
            return retval

        self.logger.debug('arithmetic op, type %s' % self.op)

        # otherwise arithmetic op
        lhs_val = self.lhs.eval_node(node, functions, symbol_table)
        rhs_val = self.rhs.eval_node(node, functions, symbol_table)

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
        elif self.op == ':=':
            if self.lhs.op != 'IDENTIFIER':
                raise SyntaxError('must assign to identifier: %s' %
                                  (self.lhs.lhs))
            self.logger.debug('setting %s to %s' % (self.lhs.lhs, rhs_val))
            self.assign_identifier(node, self.lhs.lhs, rhs_val, symbol_table)
            result = rhs_val
        else:
            raise SyntaxError('bad op token (%s)' % self.op)

        if self.negate:
            return not result

        return result


class Solver:
    def __init__(self, node, cluster, constraints, parent=None, prim=None,
                 ns={}):

        if node is None:
            raise ValueError('cannot solve without a concrete node')

        self.constraints = constraints
        self.node = node
        self.consequences = []
        self.children = []
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.solutions = {}
        self.parent = parent
        self.cluster = cluster
        self.prim = prim
        self.ns = ns

    def can_coerce(self, constraint_node, consequence_node):
        # see if the consequence expression can be forced
        # into the constraint form.

        self.logger.debug('Trying to coerce %s' % consequence_node.to_s())
        self.logger.debug('... to %s' % constraint_node.to_s())

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
            return False, {}

        if constraint_ast.op != ':=':
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
        import roush.db.api as api

        # first, build up asts of all my unsolved constraints
        f_builder = FilterBuilder(FilterTokenizer())

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
        primitives = api._model_get_all('primitives')

        unmet_primitives = []
        applied_primitives = []

        for primitive in primitives:
            self.logger.debug('evaluating primitive for constraints: %s' %
                              primitive)
            can_add = True

            if primitive['constraints'] != []:
                constraint_filter = ' AND '.join(map(lambda x: '(%s)' % x,
                                                     primitive['constraints']))
                builder = FilterBuilder(FilterTokenizer(), constraint_filter,
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
            new_node = copy.deepcopy(self.node)

            self.logger.debug('rolling node forward: %s' % new_node)

            for solved in solution['solved']:
                if not solved in constraints:
                    raise RuntimeError('constraint disappeared!')

                constraints.remove(solved)

                # and apply...
                for consequence in solution['prim']['consequences']:
                    self.logger.debug('applying consequence %s' % consequence)
                    f_builder.set_input(consequence)
                    cons_ast = f_builder.build()
                    cons_ast.eval_node(new_node, symbol_table=solution['ns'])

            self.logger.debug('node after consequence: %s' % new_node)
            new_solver = Solver(new_node, self.cluster, constraints, self,
                                solution['prim'], ns=solution['ns'])

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
        import roush.db.api as api

        if name in ns:
            return (True, ns[name])

        if arg['type'] == 'interface':
            iname = arg['name']
            int_query = 'filter_type="interface" and name="%s"' % iname
            iface = api._model_query('filters', int_query)
            if len(iface) == 0:
                return (False, 'unknown interface "%s"' % iname)

            if len(iface) > 1:
                return (False, 'multiple definitions of "%s"' % iname)

            iface_query = iface[0]['full_expr']
            nodes = api._model_query('nodes', iface_query)

            if len(nodes) == 0:
                return (False, 'unsatisifed interface "%s"' % iname)

            if len(nodes) == 1:
                return nodes[0]['id']

            return (False, 'Choice: %s' % ([x['id'] for x in nodes],))

        return (False, 'Somehow unknowable')
