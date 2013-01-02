#!/usr/bin/env python

import logging
import re


# some utility functions for inverting and
# concretizing expressions
def invert_expression(expression):
    builder = FilterBuilder(FilterTokenizer(), expression)
    root_node = builder.build()
    return root_node.invert()


def regularize_expression(expression):
    builder = FilterBuilder(FilterTokenizer(), expression)
    root_node = builder.build()
    return root_node.to_s()


def concrete_expression(expression, ns={}):
    builder = FilterBuilder(FilterTokenizer(), expression)
    root_node = builder.build()
    return root_node.concrete(ns)


def apply_expression(node, expression, api):
    """
    run an arbitrary expression on a node or node_id against
    a specific api endpoint
    """

    builder = FilterBuilder(FilterTokenizer(), expression,
                            api=api)
    root_node = builder.build()

    if not isinstance(node, dict):
        node = api._model_get_by_id('nodes', node)

    root_node.eval_node(node)


# some common utility functions for filter/expr language
def util_nth(context, n, ary):
    if not isinstance(ary, list):
        return None

    if not isinstance(n, int):
        return None

    if (len(ary) - 1) < n:
        return None

    return ary[n]


def util_str(context, what):
    if not what:
        return None

    return str(what)


def util_int(context, what):
    if not what:
        return None

    return int(what)


def util_max(context, ary):
    if not isinstance(ary, list):
        return False
    return max(ary)


def util_count(context, ary):
    if not isinstance(ary, list):
        return None
    return len(ary)


def util_union(context, listish1, listish2):
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


def util_filter(context, node_type, input_filter):
    if not 'api' in context or context['api'] is None:
        raise ValueError('no api in util_filter context')

    builder = FilterBuilder(FilterTokenizer(), "%s: %s" % (node_type,
                                                           input_filter),
                            api=context['api'])

    result = builder.filter()
    return result


def util_ifcount(context, iface_name):
    if not 'api' in context or context['api'] is None:
        raise ValueError('no api in util_ifcount context')

    interface_query = 'filter_type="interface" and name="%s"' % iface_name
    filter_list = FilterBuilder(FilterTokenizer(), '%s: %s' %
                                ('filters', interface_query),
                                api=context['api']).filter()

    if len(filter_list) != 1:
        raise SyntaxError('bad interface type %s' % iface_name)

    ifaces_query = filter_list[0]['full_expr']

    ifaces = FilterBuilder(FilterTokenizer(), '%s: %s' %
                           ('nodes', ifaces_query),
                           api=context['api']).filter()
    return len(ifaces)


def util_printf(context, fmt, *args):
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
                 ns={}, api=None):
        self.tokenizer = tokenizer
        self.input_expression = input_expression
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.logger.debug('New builder on expression: %s' %
                          self.input_expression)
        self.functions = functions
        self.ns = ns

        self.api = api

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
                 ns={}, api=None):
        super(FilterBuilder, self).__init__(tokenizer, input_expression,
                                            functions=functions,
                                            ns=ns,
                                            api=api)
        self.input_type = input_type

    def parse(self):
        return self.parse_phrase()

    def filter(self, input_type=None):
        if self.api is None:
            raise ValueError('no api data source set')

        # get a list of all the self.input_types, and eval each in turn
        root_node = self.build()

        if input_type is None:
            self.logger.debug('unspecified input type, using %s' %
                              self.input_type)
            input_type = self.input_type

        if input_type is None:
            raise SyntaxError('unknown filter type')

        nodes = self.api._model_get_all(input_type)

        result = []

        for node in nodes:
            self.logger.debug('Checking node %s' % node['id'])
            if root_node.eval_node(node, self.functions, self.ns):
                result.append(node)

        self.logger.debug("Found %d results" % len(result))
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
            return Node(lhs, op, rhs, negate, api=self.api)
        else:
            return lhs

    # evaulable_item -> function(evalable_item, ...) | identifier | value
    def parse_evaluable_item(self):
        token, val = self.tokenizer.scan()

        if token == 'NUMBER':
            return Node(int(val), 'NUMBER', None, api=self.api)

        if token == 'STRING':
            return Node(str(val), 'STRING', None, api=self.api)

        if token == 'BOOL':
            return Node(val, 'BOOL', None, api=self.api)

        if token == 'NONE':
            return Node(None, 'NONE', None, api=self.api)

        if token == 'IDENTIFIER':
            next_token, next_val = self.tokenizer.peek()
            if next_token != 'OPENPAREN':
                return Node(str(val), 'IDENTIFIER', None, api=self.api)
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
                        return Node(function_name, 'FUNCTION', args,
                                    api=self.api)

                    if token != 'COMMA':
                        raise SyntaxError('expecting comma or close paren')

        raise SyntaxError('expecting evaluable item in "%s"' %
                          self.input_expression)

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
            return Node(node, 'OR', rhs, api=self.api)
        else:
            return node

    # andexpr -> orexpr { T_AND orexpr }
    def parse_andexpr(self):
        node = self.parse_orexpr()

        token, val = self.tokenizer.peek()
        if token == 'AND':
            self.tokenizer.scan()  # eat the token
            rhs = self.parse_andexpr()
            return Node(node, 'AND', rhs, api=self.api)
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
    def __init__(self, lhs, op, rhs, negate=False, api=None):
        self.lhs = lhs
        self.rhs = rhs
        self.op = op
        self.negate = negate
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.api = api

    def concrete(self, ns):
        if self.op in ['NUMBER', 'BOOL', 'NONE']:
            return self.value_to_s(ns)

        if self.op in ['STRING', 'IDENTIFIER']:
            string = self.canonicalize_string(self.lhs, ns)
            if self.op == 'STRING':
                string = "'%s'" % string.replace("'", "\'")
            return string

        if self.op == 'FUNCTION':
            return '%s(%s)' % (
                self.lhs, ', '.join(map(lambda x: x.concrete(ns),
                                        self.rhs)))

        if self.op == 'AND' or self.op == 'OR':
            return '(%s) %s (%s)' % (self.lhs.concrete(ns),
                                     self.op,
                                     self.rhs.concrete(ns))

        return '%s %s%s %s' % (self.lhs.concrete(ns),
                               '!' if self.negate else '',
                               self.op,
                               self.rhs.concrete(ns))

    def canonicalize_string(self, string, ns):
        result = string

        match = re.match("(.*)\{(.*?)}(.*)", string)
        if match is not None:
            start = match.group(1)
            term = match.group(2)
            end = match.group(3)

            if term in ns:
                result = "%s%s%s" % (start,
                                     ns[term],
                                     self.canonicalize_string(end, ns))
            else:
                result = "%s{%s}%s" % (start,
                                       term,
                                       self.canonicalize_string(end, ns))

        return result

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

            self.logger.debug('self.lhs.op: %s' % self.lhs.op)
            self.logger.debug('self.rhs.op: %s' % self.rhs.op)
            self.logger.debug('self.rhs.lhs: %s' % self.rhs.lhs)
            self.logger.debug('self.lhs.lhs: %s' % self.lhs.lhs)
            self.logger.debug('self.rhs.rhs[0]: %s' % self.rhs.rhs[0])

            if (self.lhs.op == 'IDENTIFIER' and (
                    self.rhs.op == 'FUNCTION' and (
                        self.rhs.lhs == 'union'))):
                return ['%s in %s' % (self.rhs.rhs[1].value_to_s(),
                                      self.rhs.rhs[0].value_to_s())]

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

    def assign_identifier(self, node, identifier, value, symbol_table={},
                          object_type='nodes'):
        # there are all kinds of places where this can go wrong.
        # we can create arbitrary facts, but not attributes, and here
        # we are just assuming that an expressed consequence is a valid
        # one.
        #
        # right now we'll assume that if this is expressed as a consequence,
        # it's actually realizable in the underlying data structure.  If not,
        # well... bad things.
        self.logger.debug('assigning id using api: %s' % self.api)

        if not identifier:
            return None

        self.logger.debug('setting %s to %s' % (identifier, value))
        canonical = self.canonicalize_identifier(node, identifier,
                                                 symbol_table)

        self.logger.debug('canonicalized %s to %s' % (identifier, canonical))
        if canonical.find('.') == -1:
            # do an update on this node.
            self.api._model_update_by_id(object_type, node['id'],
                                         {canonical: value})
            return
        else:
            (attr, rest) = canonical.split('.', 1)

            self.logger.debug('attr: %s, object_type: %s' %
                              (attr, object_type))

            if attr == 'facts' and object_type == 'nodes':
                existing_fact = self.api._model_query(
                    'facts',
                    'node_id=%d and key=%s' % (node['id'], rest))

                if existing_fact:
                    self.api._model_update_by_id('facts',
                                                 existing_fact['id'],
                                                 {'value': value})
                else:
                    self.api._model_create('facts', {'node_id': node['id'],
                                                     'key': rest,
                                                     'value': value})
            elif attr == 'attrs' and object_type == 'nodes':
                existing_attr = self.api._model_query(
                    'attrs',
                    'node_id=%d and key=%s' % (node['id'], rest))

                if existing_attr:
                    self.api._model_update_by_id('attrs',
                                                 existing_attr['id'],
                                                 {'value': value})
                else:
                    self.api._model_create('attrs', {'node_id': node['id'],
                                                     'key': rest,
                                                     'value': value})
            return

        raise ValueError('Cannot express assignment to id: %s' % identifier)

    def eval_identifier(self, node, identifier, symbol_table={}):
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
                        new_node = self.api._model_get_by_id("%ss" %
                                                             attr, the_id)
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

        if self.api is None:
            raise ValueError('evaluating a node without a corresponding api.')

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

                retval = functions[self.lhs]({'api': self.api}, *args)

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
