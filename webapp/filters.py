#!/usr/bin/env python

import logging
import re
import sys

import db.database
from db import api


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
            (r"[ \t\n]+", None),
            (r"[0-9]+", self.number),
            (r"\(", self.open_paren),
            (r"\)", self.close_paren),
            (r"'((?:[^'\\]|\\.)*)'", self.qstring),
            (r"[a-zA-Z_]*:", self.typedef),
            (r"\<\=|\>\=", self.op),
            (r"\=|\<|\>", self.op),
            (r"[A-Za-z_\.]*", self.identifier),
            (r"'((?:[^'\\]|\\.)*)'", self.qstring),
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

    def qstring(self, scanner, token):
        return 'STRING', token[1:-1]

    def open_paren(self, scanner, token):
        return 'OPENPAREN', token

    def close_paren(self, scanner, token):
        return 'CLOSEPAREN', token

    def or_op(self, scanner, token):
        return 'OR', token

    def and_op(self, scanner, token):
        return 'AND', token

    def parse(self, input_filter):
        self.tokens, self.remainder = self.scanner.scan(input_filter)
        self.tokens.append(('EOF', None))

        if self.remainder != '':
            raise RuntimeError(
                'Cannot parse.  Input: %s, remainder %s' %
                (input_filter, self.remainder))

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
# phrase -> typedef andexpr EOF
# andexpr -> orexpr { T_AND orexpr }
# orexpr -> expr { T_OR expr }
# expr -> T_OPENPAREN andexpr T_CLOSEPAREN | criterion
# criterion -> field { uneg } op value
#
# field -> datatype.value
# op -> '=', '<', '>'
# value -> number |
#
# Lots of small problems here.. nodes should probably
# store both tokens and
class AstBuilder:
    def __init__(self, tokenizer, input_filter):
        self.tokenizer = tokenizer
        self.input_filter = input_filter
        self.logger = logging.getLogger('filter.astbuilder')
        self.logger.debug('Running input filter %s' % input_filter)

    def build(self):
        self.tokenizer.parse(self.input_filter)

        root_node = self.parse_phrase()
        return root_node

    def eval(self):
        # get a list of all the self.filter_types, and eval each in turn
        root_node = self.build()
        nodes = api._model_get_all(self.filter_type)

        result = []

        for node in nodes:
            logging.debug('Checking node %s' % node['id'])
            if root_node.eval_node(node):
                result.append(node)

        logging.debug("Found %d results" % len(result))

        return result

    # criterion -> field { uneg } op value
    def parse_criterion(self):
        token, val = self.tokenizer.scan()

        if token != 'IDENTIFIER':
            raise RuntimeError('expecting identifier')

        lhs = val
        token, val = self.tokenizer.scan()
        if token != 'OP':
            raise RuntimeError('expecting operator')

        op = val

        token, val = self.tokenizer.scan()
        if token == 'NUMBER':
            rhs = int(val)
        elif token == 'STRING':
            rhs = val
        else:
            raise RuntimeError('expecting STRING or NUMBER')

        return Node(lhs, op, rhs)

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
            rhs = self.parse_orexpr()
            return Node(node, 'AND', rhs)
        else:
            return node

    # phrase -> typedef andexpr EOF
    def parse_phrase(self):
        token, val = self.tokenizer.scan()

        if token != 'TYPEDEF':
            raise RuntimeError('missing typedef')

        self.filter_type = val

        node = self.parse_andexpr()

        token, val = self.tokenizer.scan()
        if token != 'EOF':
            raise RuntimeError('expecting EOF')

        return node


class Node:
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.rhs = rhs
        self.op = op
        self.logger = logging.getLogger('filter.node')

    def dotty(self, fd):
        fd.write('"%s" [label = "%s"]' % (id(self), self.op) + ';\n')

        lhs_id = 'x'
        rhs_id = 'x'

        if isinstance(self.lhs, 3) or isinstance(self.lhs, 'x'):
            lhs_id = str(id(self)) + "lhs"
            lhs_label = str(self.lhs)
            fd.write('"%s" [label = "%s"]' % (lhs_id, lhs_label) + ';\n')
        else:
            lhs_id = id(self.lhs)
            self.lhs.dotty(fd)

        if isinstance(self.rhs, 3) or isinstance(self.rhs, 'x'):
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
        (obj, attr) = identifier.split('.', 1)

        self.logger.debug('checking %s in linked object %s' % (attr, obj))

        if "%s%s" % (obj, '_id') in node:
            the_id = node["%s%s" % (obj, '_id')]
            if the_id:
                self.logger.debug('found linked object type %s with id: %s' %
                                  (obj, str(the_id)))
                try:
                    # grab the linked object...
                    new_node = api._model_get_by_id("%ss" % obj, the_id)
                    self.logger.debug("Indirected object: %s" % new_node)
                except Exception as e:
                    self.logger.debug('cannot lookup the object type: %s' %
                                      str(e))
                    return None

                return self.eval_identifier(new_node, attr)
            else:
                return None

    def eval_node(self, node):
        rhs_val = None
        lhs_val = None

        if isinstance(self.lhs, Node):
            lhs_val = self.lhs.eval_node(node)
        else:
            lhs_val = self.eval_identifier(node, self.lhs)

        if isinstance(self.rhs, Node):
            rhs_val = self.rhs.eval_node(node)
        else:
            rhs_val = self.rhs

        self.logger.debug('evaluating %s (%s) %s %s (%s)' %
                          (self.lhs, lhs_val, self.op,
                           self.rhs, str(rhs_val)))

        if self.op == '=':
            if rhs_val == lhs_val:
                return True
            return False
        elif self.op == '<':
            if rhs_val < lhs_val:
                return True
            return False
        elif self.op == '>':
            if rhs_val > lhs_val:
                return True
            return False
        elif self.op == 'AND':
            return lhs_val and rhs_val
        elif self.op == 'OR':
            return lhs_val or rhs_val
        else:
            raise RuntimeError('bad op token (%s)' % self.op)

if __name__ == '__main__':
    from db.database import init_db

    from sqlalchemy.orm import sessionmaker, create_session, scoped_session
    from sqlalchemy.ext.declarative import declarative_base

    db.database.init_db('sqlite:///roush.db')
    db_session = scoped_session(lambda: create_session(autocommit=False,
                                                       autoflush=False,
                                                       bind=engine))

    logging.basicConfig(level=logging.DEBUG)

    Base = declarative_base()
    Base.query = db_session.query_property()

    if len(sys.argv) > 1:
        input_filter = sys.argv[1]
    else:
        input_filter = "nodes: hostname = 'airbook'"

    builder = AstBuilder(FilterTokenizer(), input_filter)
    result = builder.eval()

    logging.debug("%s" % result)
