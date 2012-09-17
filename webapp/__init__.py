#!/usr/bin/env python

import daemon
import fcntl
import getopt
import logging
import os
import sys
import traceback

from ConfigParser import ConfigParser
from flask import Flask
from clusters import clusters
from nodes import nodes
from roles import roles
from index import index
from tasks import tasks

import backends

backend = None


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

        defaults = {'main':
                    {'bind_address': '0.0.0.0',
                     'bind_port': 8080,
                     'backend': 'null',
                     'loglevel': 'WARNING',
                     'database_uri': 'sqlite:///',
                     'daemonize': False,
                     'pidfile': None},
                    'opscodechef_backend':
                    {'role_location': '/etc/roush/roles.d'},
                    'null_backend': {}}

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

        backend_module = defaults['main']['backend']
        self.backend = backends.load(
            backend_module, defaults['%s_backend' % backend_module])
        self.config.update(defaults['main'])

        LOG = logging.getLogger()

        if debug:
            LOG.setLevel(logging.DEBUG)
        elif 'loglevel' in defaults['main']:
            LOG.setLevel(defaults['main']['loglevel'])
        else:
            LOG.setLevel(logging.WARNING)

        print("daemonize: %s, debug: %s, configfile: %s, loglevel: %s " \
                % (daemonize,
                   debug,
                   configfile,
                   logging.getLevelName(LOG.getEffectiveLevel())))

        if 'logfile' in defaults['main']:
            for handler in LOG.handlers:
                LOG.removeHandler(handler)

            handler = logging.FileHandler(defaults['main']['logfile'])
            LOG.addHandler(handler)

        self.register_blueprint(index)
        self.register_blueprint(clusters, url_prefix='/clusters')
        self.register_blueprint(nodes, url_prefix='/nodes')
        self.register_blueprint(roles, url_prefix='/roles')
        self.register_blueprint(tasks, url_prefix='/tasks')
        self.testing = debug

        if debug:
            self.config['TESTING'] = True

        if daemonize:
            self.config['daemonize'] = True

    def run(self):
        context = None

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
            if logging.isEnabledFor(logging.DEBUG):
                print ''
                traceback.print_exception(*exc_info)
                sys.exit(1)
            else:
                sys.exit(retval)
        finally:
            if context:
                context.close()
