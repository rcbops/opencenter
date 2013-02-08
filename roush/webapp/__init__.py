#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import daemon
import fcntl
import getopt
import logging
import os
import random
import string
import sys
import traceback
import time

from ConfigParser import ConfigParser
from flask import Flask, jsonify, request

# from roush import backends
from roush.db import models
from roush.db.api import api_from_models
from roush.webapp import generic
from roush.webapp import utility
from roush.webapp.ast import FilterBuilder, FilterTokenizer
from roush.webapp.adventures import bp as adventures_bp
from roush.webapp.attrs import bp as attrs_bp
from roush.webapp.facts import bp as facts_bp
from roush.webapp.facts_please import bp as facts_please
from roush.webapp.filters import bp as filters_bp
from roush.webapp.index import bp as index_bp
from roush.webapp.nodes import bp as nodes_bp
# from roush.webapp.nodes_please import bp as nodes_please
from roush.webapp.plan import bp as plan_bp
from roush.webapp.primitives import bp as primitives_bp
from roush.webapp.tasks import bp as tasks_bp


# api = api_from_models()


# Stolen: http://code.activestate.com/recipes/\
#         577911-context-manager-for-a-daemon-pid-file/
class PidFile(object):
    def __init__(self, path):
        self.path = path
        self.pidfile = None

    def __enter__(self):
        self.pidfile = open(self.path, 'a+')
        try:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise SystemExit('Pid file in use')

        self.pidfile.seek(0)
        self.pidfile.truncate()
        self.pidfile.write(str(os.getpid()))
        self.pidfile.flush()
        self.pidfile.seek(0)
        return self.pidfile

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        try:
            self.pidfile.close()
        except IOError as err:
            if err.errno != 9:
                raise
        os.remove(self.path)


class Thing(Flask):
    def __init__(self, name, argv=None, configfile=None,
                 confighash=None, debug=False):
        daemonize = False
        self.registered_models = []
        self.transactions = {
            'session_key': "".join([random.choice(string.hexdigits)
                                   for n in xrange(30)])}

        super(Thing, self).__init__(name)

        if argv:
            try:
                opts, args = getopt.getopt(argv, 'c:vd',
                                           ['config=', 'verbose', 'daemonize'])
            except getopt.GetoptError as err:
                print str(err)
                self.usage()
                sys.exit(1)

            for o, a in opts:
                if o in ('-c', '--config'):
                    configfile = a
                elif o in ('-v', '--verbose'):
                    debug = True
                elif o in ('-d', '--daemonize'):
                    daemonize = True
                else:
                    print "Bad option"
                    self.usage()
                    sys.exit(1)

            sys.argv = [sys.argv[0]] + args

        defaults = {
            'logging': {},
            'main': {
                'bind_address': '0.0.0.0',
                'bind_port': 8080,
                'backend': '/dev/null',
                'loglevel': 'WARNING',
                'database_uri': 'sqlite:///',
                'daemonize': False,
                'pidfile': None
            },
            'ChefClientBackend': {
                'role_location': '/etc/roush/roles.d'},
            'ChefServerBackend': {},
            'UnprovisionedBackend': {}
        }

        if configfile:
            config = ConfigParser()
            config.read(configfile)

            configfile_hash = dict(
                [(s, dict(config.items(s))) for s in config.sections()])

            for section in configfile_hash:
                if section in defaults:
                    defaults[section].update(configfile_hash[section])
                else:
                    defaults[section] = configfile_hash[section]

        if confighash:
            defaults.update(confighash)

        logging.basicConfig(level=logging.WARNING)
        LOG = logging.getLogger()

        if debug:
            LOG.setLevel(logging.DEBUG)
        elif 'loglevel' in defaults['main']:
            LOG.setLevel(defaults['main']['loglevel'])
        else:
            LOG.setLevel(logging.WARNING)

        if 'logfile' in defaults['main']:
            for handler in LOG.handlers:
                LOG.removeHandler(handler)

            handler = logging.FileHandler(defaults['main']['logfile'])
            LOG.addHandler(handler)
        self._logger = LOG

        # Allow for logging section to overload specific children LogLevels
        if 'logging' in defaults:
            overrides = defaults['logging'].keys()
            for ns in overrides:
                TMP_LOG = logging.getLogger(ns)
                TMP_LOG.setLevel(defaults['logging'][ns].upper())

        # # load the backends
        # backends.load(defaults['main']['backend'], defaults)

        # set the notification dispatcher
        # self.dispatch = backends.notify

        self.config.update(defaults['main'])

        print("daemonize: %s, debug: %s, configfile: %s, loglevel: %s " %
              (daemonize, debug, configfile,
               logging.getLevelName(LOG.getEffectiveLevel())))

        self.register_blueprint(index_bp)
        self.register_blueprint(nodes_bp, url_prefix='/nodes')
        self.register_blueprint(nodes_bp, url_prefix='/admin/nodes')
        self.register_blueprint(tasks_bp, url_prefix='/tasks')
        self.register_blueprint(tasks_bp, url_prefix='/admin/tasks')
        self.register_blueprint(adventures_bp, url_prefix='/adventures')
        self.register_blueprint(adventures_bp, url_prefix='/admin/adventures')
        self.register_blueprint(filters_bp, url_prefix='/filters')
        self.register_blueprint(filters_bp, url_prefix='/admin/filters')
        self.register_blueprint(facts_please, url_prefix='/facts')
        self.register_blueprint(facts_bp, url_prefix='/admin/facts')
        self.register_blueprint(attrs_bp, url_prefix='/attrs')
        self.register_blueprint(attrs_bp, url_prefix='/admin/attrs')
        self.register_blueprint(primitives_bp, url_prefix='/primitives')
        self.register_blueprint(primitives_bp, url_prefix='/admin/primitives')
        self.register_blueprint(plan_bp, url_prefix='/plan')
        self.register_blueprint(plan_bp, url_prefix='/admin/plan')
        self.testing = debug

        # Define transaction dict for all models
        for model in self.registered_models:
            self.transactions[model] = {time.time(): set([])}

        if debug:
            self.config['TESTING'] = True

        if daemonize:
            self.config['daemonize'] = True

    def usage(self):
        """Print a usage message."""

        print """The following command line flags are supported:

[-c|--config] <file>: use this config file
[-v|--verbose]:       include if you want verbose logging
[-d|--deamonize]:     if set then roush will run as a daemon"""

    def register_blueprint(self, blueprint, url_prefix='/', **kwargs):
        super(Thing, self).register_blueprint(blueprint,
                                              url_prefix=url_prefix,
                                              **kwargs)

        # auto-register the schema url
        def schema_details(what):
            def f():
                api = api_from_models()
                return jsonify({"schema": api._model_get_schema(what)})
            return f

        def filter_object(what):
            def f():
                resp = None

                builder = FilterBuilder(
                    FilterTokenizer(),
                    '%s: %s' % (what, request.json['filter']),
                    api=api_from_models())

                # try:
                result = builder.filter()
                resp = jsonify({'status': 200,
                                'message': 'success',
                                what: result})
                # except SyntaxError as e:
                #     resp = jsonify({'status': 400,
                #                     'message': 'Syntax error: %s' % e.msg})
                #     resp.status_code = 400

                return resp
            return f

        def filter_object_by_id(what):
            def f(filter_id):
                api = api_from_models()
                filter_obj = api.filter_get_by_id(filter_id)
                full_expr = filter_obj['full_expr']
                builder = FilterBuilder(FilterTokenizer(),
                                        '%s: %s' % (what, full_expr))

                return jsonify({what: builder.filter()})

            return f

        def updates_by_txid(what):
            def f(session_key, txid):
                """
                Accepts a transaction id, and returns a list of
                updated nodes from input transaction_id to latest
                transaction_id.  transaction dict.

                FIXME: As an optimization, the changes could be
                accumulated in a single set up until the point
                that someone got a new txid.  Then we could avoid
                having a long list of one-element transactions, and
                instead only create db version intervals on the intervals
                that we know people could possibly refer from.  If that
                makes sense.

                Arguments:
                txid -- transaction id (opaque)

                Returns:

                session_key -- unique session key

                nodes -- list of updated node_ids from trx_id to
                latest transaction id
                """

                trans = self.transactions[what]
                current_txid = time.time()

                if session_key != self.transactions['session_key']:
                    return generic.http_response(410, 'Invalid session_key')

                txid = float(txid)

                if 'poll' in request.args:
                    # we'll poll if we have no changes
                    if txid >= max(trans.keys()):
                        semaphore = '%s-changes' % (what)
                        utility.wait(semaphore)

                if txid < min(trans.keys()):
                    return generic.http_response(410, 'Expired transaction id')

                retval = set([])
                for x in [trans[tx] for tx in trans.keys() if tx > txid]:
                    retval = retval.union(x)

                return generic.http_response(
                    200, 'Updated %s' % what.title(),
                    **{"transaction": {'session_key': session_key,
                                       'txid': '%.6f' % current_txid},
                       what: list(retval)})
            return f

        def root_schema():
            schema = {'schema': {'objects': self.registered_models}}
            return jsonify(schema)

        def root_updates():
            """Returns the latest transaction information from the
            in-memory transaction dict.  Realize that this is only
            accurate at the time of the request.  So clearly, one
            should call this BEFORE serializing stuffs.

            Arguments:
            None

            Returns:
            json object containing: the unique session key,
                                    the latest transaction id
            """
            session_key = self.transactions['session_key']
            txid = time.time()

            return generic.http_response(
                transaction={'session_key': session_key,
                             'txid': '%.6f' % txid})

        bpname = blueprint.name
        if bpname.endswith('_please'):
            bpname = bpname.split('_')[0]

        if url_prefix != '/' and hasattr(models, bpname.capitalize()):
            self._logger.debug('registering %s at %s' % (blueprint.name,
                                                         url_prefix))

            self._logger.debug('mangling name to %s' % bpname)

            if not url_prefix.startswith('/admin/'):
                self.registered_models.append(bpname)

            url = '%s/schema' % (url_prefix,)
            self.add_url_rule(url, '%s.schema' % blueprint.name,
                              schema_details(bpname),
                              methods=['GET'])
            filter_url = '%s/filter' % (url_prefix,)
            self.add_url_rule(filter_url, '%s.filter' % blueprint.name,
                              filter_object(bpname),
                              methods=['POST'])
            f_id_url = '%s/filter/<filter_id>' % (url_prefix,)
            self.add_url_rule(f_id_url, '%s.filter_by_id' % blueprint.name,
                              filter_object_by_id(bpname),
                              methods=['GET'])

            txid_url = '%s/updates/<session_key>/<txid>' % (url_prefix,)
            self.add_url_rule(txid_url, '%s.txid' % blueprint.name,
                              updates_by_txid(bpname),
                              methods=['GET'])

        elif url_prefix == '/':
            self.add_url_rule('/schema', 'root.schema',
                              root_schema,
                              methods=['GET'])
            self.add_url_rule('/admin/schema', 'admin.schema',
                              root_schema,
                              methods=['GET'])
            self.add_url_rule('/updates', 'root.updates',
                              root_updates,
                              methods=['GET'])
            self.add_url_rule('/admin/updates', 'admin.updates',
                              root_updates,
                              methods=['GET'])

    def run(self):
        context = None

        LOG = logging.getLogger()

        if self.config['daemonize']:
            pidfile = None
            if self.config['pidfile']:
                pidfile = PidFile(self.config['pidfile'])

            context = daemon.DaemonContext(
                working_directory='/',
                umask=0o022,
                pidfile=pidfile)

        try:
            if context:
                context.open()

            super(Thing, self).run(host=self.config['bind_address'],
                                   port=self.config['bind_port'])
        except KeyboardInterrupt:
            sys.exit(1)
        except SystemExit:
            raise
        except:
            exc_info = sys.exc_info()
            if hasattr(exc_info[0], "__name__"):
                exc_class, exc, tb = exc_info
                tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                logging.error("%s (%s:%s in %s)", exc_info[1], tb_path,
                              tb_lineno, tb_func)
            else:  # string exception
                logging.error(exc_info[0])
            if LOG.isEnabledFor(logging.DEBUG):
                print ''
                traceback.print_exception(*exc_info)
                sys.exit(1)
            else:
                sys.exit(1)
        finally:
            if context:
                context.close()
