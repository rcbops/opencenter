#!/usr/bin/env python

from ConfigParser import ConfigParser
from flask import Flask
from clusters import clusters
from nodes import nodes
from roles import roles

import backends
import logging

backend = None

class Thing:
    def __init__(self, **kwargs):
        configfile = kwargs.get('configfile', None)
        confighash = kwargs.get('confighash', None)
        debug = kwargs.get('debug', False)

        defaults = { 'main':
                     { 'bind_address': '0.0.0.0',
                       'bind_port': 8080,
                       'backend': 'null',
                       'loglevel': 'WARNING' },
                     'opscodechef_backend':
                     { 'role_location': '/etc/roush/roles.d' },
                     'null_backend': {}}

        if configfile:
            config = ConfigParser()
            config.read(configfile)

            defaults.update(
                dict([(s, dict(config.items(s))) for s in config.sections()]))

        if confighash:
            defaults.update(confighash)

        backend_module = defaults['main']['backend']
        backend = backends.load(
            backend_module, defaults['%s_backend' % backend_module])
        self.config = defaults['main']

        self.app = Flask('roush')
        self.app.register_blueprint(clusters, url_prefix='/clusters')
        self.app.register_blueprint(nodes, url_prefix='/nodes')
        self.app.register_blueprint(roles, url_prefix='/roles')

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

        self.app.testing = debug

    def run(self):
        self.app.run(host = self.config['bind_address'],
                     port = self.config['bind_port'])

    def test_client(self):
        result = self.app.test_client()
        LOG = logging.getLogger()
        LOG.addHandler(logging.FileHandler("./stupid.log"))
        LOG.setLevel(logging.DEBUG)

        return result
