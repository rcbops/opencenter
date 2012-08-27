#!/usr/bin/env python

from ConfigParser import ConfigParser
from flask import Flask
from clusters import clusters
from nodes import nodes
from roles import roles

import backends
import logging

backend = None


class Thing(Flask):
    def __init__(self, name, configfile=None, confighash=None, debug=False):
        super(Thing, self).__init__(name)

        defaults = {'main':
                    {'bind_address': '0.0.0.0',
                     'bind_port': 8080,
                     'backend': 'null',
                     'loglevel': 'WARNING',
                     'database_uri': 'sqlite:///:memory:'},
                    'opscodechef_backend':
                    {'role_location': '/etc/roush/roles.d'},
                    'null_backend': {}}

        if configfile:
            config = ConfigParser()
            config.read(configfile)

            defaults.update(
                dict([(s, dict(config.items(s))) for s in config.sections()]))

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

        self.register_blueprint(clusters, url_prefix='/clusters')
        self.register_blueprint(nodes, url_prefix='/nodes')
        self.register_blueprint(roles, url_prefix='/roles')
        self.testing = debug

    def run(self):
        super(Thing, self).run(host=self.config['bind_address'],
                               port=self.config['bind_port'])
