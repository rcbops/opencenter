#!/usr/bin/env python

import daemon
import fcntl
import os

from ConfigParser import ConfigParser
from flask import Flask
from clusters import clusters
from nodes import nodes
from roles import roles
from index import index
from tasks import tasks

import backends
import logging

backend = None

# Stolen: http://code.activestate.com/recipes/577911-context-manager-for-a-daemon-pid-file/
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

    def __exit__(self, exc_type = None, exc_value = None, exc_tb = None):
        try:
            self.pidfile.close()
        except IOError as err:
            if err.errno != 9:
                raise
        os.remove(self.path)


class Thing(Flask):
    def __init__(self, name, configfile=None, confighash=None, debug=False):
        super(Thing, self).__init__(name)

        defaults = {'main':
                    {'bind_address': '0.0.0.0',
                     'bind_port': 8080,
                     'backend': 'null',
                     'loglevel': 'WARNING',
                     'database_uri': 'sqlite:///',
                     'daemonize': False,
                     'pidfile': None },
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
        else:
            LOG.setLevel(logging.WARNING)

        if 'logfile' in defaults['main']:
            for handler in LOG.handlers:
                LOG.removeHandler(handler)

            handler = logging.FileHandler(defaults['main']['logfile'])
            LOG.addHandler(handler)

        if 'loglevel' in defaults['main']:
            LOG.setLevel(defaults['main']['loglevel'])

        self.register_blueprint(index)
        self.register_blueprint(clusters, url_prefix='/clusters')
        self.register_blueprint(nodes, url_prefix='/nodes')
        self.register_blueprint(roles, url_prefix='/roles')
        self.register_blueprint(tasks, url_prefix='/tasks')
        self.testing = debug

        if debug:
            self.config['TESTING'] = True

    def run(self):
        if self.config['daemonize']:
            pidfile = None
            if self.config['pidfile']:
                pidfile = PidFile(self.config['pidfile'])

            context = daemon.DaemonContext(
                working_directory = '/',
                umask = 0o022,
                pidfile = pidfile)

            with context:
                self._run()
        else:
            self._run()

    def _run(self):
        super(Thing, self).run(host=self.config['bind_address'],
                               port=self.config['bind_port'])
