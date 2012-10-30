#!/usr/bin/env python

import daemon
import fcntl
import getopt
import logging
import os
import sys
import traceback

from ConfigParser import ConfigParser
from flask import Flask, jsonify, request
from adventures import adventures
from clusters import clusters
from nodes import nodes
from index import index
from tasks import tasks
from filters import filters

from ast import AstBuilder, FilterTokenizer

from db import api, models, database

import backends


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

        super(Thing, self).__init__(name)

        if argv:
            try:
                opts, args = getopt.getopt(argv, 'c:vd')
            except getopt.GetoptError as err:
                print str(err)
                sys.exit(1)

            for o, a in opts:
                if o == '-c':
                    configfile = a
                elif o == '-v':
                    debug = True
                elif o == '-d':
                    daemonize = True
                else:
                    print "Bad option"
                    sys.exit(1)

            sys.argv = [sys.argv[0]] + args

        defaults = {'main':
                    {'bind_address': '0.0.0.0',
                     'bind_port': 8080,
                     'backend': '/dev/null',
                     'loglevel': 'WARNING',
                     'database_uri': 'sqlite:///',
                     'daemonize': False,
                     'pidfile': None},
                    'ChefClientBackend':
                    {'role_location': '/etc/roush/roles.d'},
                    'ChefServerBackend': {},
                    'UnprovisionedBackend': {}}

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

        # load the backends
        backends.load(defaults['main']['backend'], defaults)

        # set the notification dispatcher
        self.dispatch = backends.notify

        self.config.update(defaults['main'])

        print("daemonize: %s, debug: %s, configfile: %s, loglevel: %s " %
              (daemonize, debug, configfile,
               logging.getLevelName(LOG.getEffectiveLevel())))

        self.register_blueprint(index)
        self.register_blueprint(clusters, url_prefix='/clusters')
        self.register_blueprint(nodes, url_prefix='/nodes')
        self.register_blueprint(tasks, url_prefix='/tasks')
        self.register_blueprint(adventures, url_prefix='/adventures')
        self.register_blueprint(filters, url_prefix='/filters')
        self.testing = debug

        if debug:
            self.config['TESTING'] = True

        if daemonize:
            self.config['daemonize'] = True

    def register_blueprint(self, blueprint, url_prefix='/', **kwargs):
        super(Thing, self).register_blueprint(blueprint,
                                              url_prefix=url_prefix,
                                              **kwargs)

        # auto-register the schema url
        def schema_details(what):
            def f():
                return jsonify(api._model_get_schema(what))
            return f

        def filter_object(what):
            def f():
                builder = AstBuilder(FilterTokenizer(),
                                     '%s: %s' % (what, request.json['filter']))
                return jsonify({what: builder.eval()})
            return f

        def filter_object_by_id(what):
            def f(filter_id):
                print 'realizing filter %s' % filter_id

                filter_obj = api.filter_get_by_id(filter_id)
                full_expr = filter_obj['full_expr']
                builder = AstBuilder(FilterTokenizer(),
                                     '%s: %s' % (what, full_expr))

                result = {'name': filter_obj['name'],
                          'id': filter_obj['id'],
                          'nodes': [],
                          'containers': []}

                eval_result = builder.eval()

                result['nodes'] = [x['id'] for x in eval_result if x['filter_id'] == None]

                child_filters = api._model_get_by_filter('filters', {'parent_id': filter_id})
                container_list = [x['id'] for x in child_filters] if child_filters else []

                for container in container_list:
                    result['containers'].append(f(container))

                return result

            def aggregate_nodes(result_dict):
                nodelist = []
                for container in result_dict['containers']:
                    nodelist += aggregate_nodes(container)
                return nodelist

            def prune(result_dict):
                subnodelist = []

                for container in result_dict['containers']:
                    subnodelist += prune(container)

                for d in subnodelist:
                    result_dict['nodes'].remove(d)

                subnodelist += result_dict['nodes']
                return subnodelist

            def jsonify_result(filter_id):
                result = f(filter_id)
                prune(result)
                return jsonify({'results': result})

            return jsonify_result

        def root_schema():
            schema = {'schema': {'objects': self.registered_models}}
            return jsonify(schema)

        if url_prefix != '/' and hasattr(models, blueprint.name.capitalize()):
            self.registered_models.append(blueprint.name)
            url = '/%s/schema' % (blueprint.name,)
            self.add_url_rule(url, '%s.schema' % blueprint.name,
                              schema_details(blueprint.name),
                              methods=['GET'])
            filter_url = '/%s/filter' % (blueprint.name,)
            self.add_url_rule(filter_url, '%s.filter' % blueprint.name,
                              filter_object(blueprint.name),
                              methods=['POST'])
            specific_filter = '/%s/filter/<filter_id>' % (blueprint.name,)
            self.add_url_rule(specific_filter, '%s.filter_by_id' % blueprint.name,
                              filter_object_by_id(blueprint.name),
                              methods=['GET'])

        elif url_prefix == '/':
            self.add_url_rule('/schema', 'root.schema',
                              root_schema,
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
