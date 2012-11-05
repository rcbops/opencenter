#!/usr/bin/env python

import logging
import re
import sys


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


def util_filter(node_type, input_filter):
    builder = AstBuilder(FilterTokenizer(), "%s: %s" % (node_type,
                                                        input_filter))

    result = builder.eval()
    return result


def util_printf(fmt, *args):
    try:
        return fmt % args
    except Exception:
        return None


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
class FilterTokenizer:
    def __init__(self):
        self.scanner = re.Scanner([
            (r"!", self.negation),
            (r"or", self.or_op),
            (r"and", self.and_op),
            (r"none", self.none),
            (r"in", self.in_op),
            (r"true", self.bool_op),
            (r"false", self.bool_op),
            (r",", self.comma),
            (r"[ \t\n]+", None),
            (r"[0-9]+", self.number),
            (r"\(", self.open_paren),
            (r"\)", self.close_paren),
            (r"'([^'\\]*(?:\\.[^'\\]*)*)'", self.qstring),
            (r"\"([^\"\\]*(?:\\.[^\"\\]*)*)\"", self.qstring),
            (r"[a-zA-Z_]*:", self.typedef),
            (r"\<\=|\>\=", self.op),
            (r"\=|\<|\>", self.op),
            (r"[A-Za-z_\.]*", self.identifier),
        ])
        self.tokens = []
        self.remainer = ''
        self.logger = logging.getLogger('filter.tokenizer')

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
        return 'STRING', token[1:-1].replace("\\'", "'")

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

    def parse(self, input_filter):
        self.tokens, self.remainder = self.scanner.scan(input_filter)
        self.tokens.append(('EOF', None))

        if self.remainder != '':
            raise RuntimeError(
                'Cannot parse.  Input: %s\nTokens: %s\nRemainder %s' %
                (input_filter, self.tokens, self.remainder))

        self.logger.debug('Tokenized %s as %s' % (input_filter, self.tokens))
        return True

    def scan(self):
        self.logger.debug('popping token %s' % str(self.peek()))
        return self.tokens.pop(0)

    def peek(self):
        return self.tokens[0]


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
class AstBuilder:
    def __init__(self, tokenizer, input_filter,
                 filter_type=None, functions={'nth': util_nth,
                                              'str': util_str,
                                              'int': util_int,
                                              'max': util_max,
                                              'filter': util_filter,
                                              'count': util_count}):
        self.tokenizer = tokenizer
        self.input_filter = input_filter
        self.logger = logging.getLogger('filter.astbuilder')
        self.logger.debug('Running input filter %s' % input_filter)
        self.functions = functions
        self.filter_type = filter_type

    def build(self):
        self.tokenizer.parse(self.input_filter)

        root_node = self.parse_phrase()
        return root_node

    def eval(self):
        # avoid some circular includes
        import db.api as api

        import db.database
        from db import api

        # get a list of all the self.filter_types, and eval each in turn
        root_node = self.build()

        if not self.filter_type:
            raise RuntimeError('unknown filter type')

        nodes = api._model_get_all(self.filter_type)

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
                raise RuntimeError('Expecting {UNEG} BOOL | OP')

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
                        raise RuntimeError('expecting comma or close paren')

        raise RuntimeError('expecting evaluable item')

    # expr -> T_OPENPAREN andexpr T_CLOSEPAREN | criterion
    def parse_expr(self):
        token, val = self.tokenizer.peek()

        if token == 'OPENPAREN':
            self.tokenizer.scan()
            node = self.parse_andexpr()
            token, val = self.tokenizer.scan()
            if token != 'CLOSEPAREN':
                raise RuntimeError('expecting close paren')
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
            self.filter_type = val
            self.tokenizer.scan()

        node = self.parse_andexpr()

        token, val = self.tokenizer.scan()
        if token != 'EOF':
            raise RuntimeError('expecting EOF')

        return node


class Node:
    def __init__(self, lhs, op, rhs, negate=False):
        self.lhs = lhs
        self.rhs = rhs
        self.op = op
        self.negate = negate
        self.logger = logging.getLogger('filter.node')

    def dotty(self, fd):
        fd.write('"%s" [label = "%s"]' % (id(self), self.op) + ';\n')

        lhs_id = 'x'
        rhs_id = 'x'

        if isinstance(self.lhs, int) or isinstance(self.lhs, str):
            lhs_id = str(id(self)) + "lhs"
            lhs_label = str(self.lhs)
            fd.write('"%s" [label = "%s"]' % (lhs_id, lhs_label) + ';\n')
        else:
            lhs_id = id(self.lhs)
            self.lhs.dotty(fd)

        if isinstance(self.rhs, int) or isinstance(self.rhs, str):
            rhs_id = str(id(self)) + "rhs"
            rhs_label = str(self.rhs)
            fd.write('"%s" [label = "%s"]' % (rhs_id, rhs_label) + ';\n')
        else:
            rhs_id = id(self.rhs)
            self.rhs.dotty(fd)

        fd.write('"%s" -> "%s"' % (id(self), lhs_id) + ';\n')
        fd.write('"%s" -> "%s"' % (id(self), rhs_id) + ';\n')

    def eval_identifier(self, node, identifier):
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
                    raise RuntimeError('Cannot find external fn %s' % self.lhs)

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
                result = False
            elif lhs_val < rhs_val:
                result = True
        elif self.op == '>':
            if type(lhs_val) != type(rhs_val):
                result = False
            elif lhs_val > rhs_val:
                result = True
        elif self.op == '<=':
            if type(lhs_val) != type(rhs_val):
                result = False
            elif lhs_val <= rhs_val:
                result = True
        elif self.op == '>=':
            if type(lhs_val) != type(rhs_val):
                result = False
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
            raise RuntimeError('bad op token (%s)' % self.op)

        if self.negate:
            return not result

        return result
