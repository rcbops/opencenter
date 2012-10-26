#!/usr/bin/env python

import sys

from gevent.pywsgi import WSGIServer

from db.database import init_db
from webapp import Thing

if __name__ == '__main__':
    foo = Thing("roush", argv=sys.argv[1:], configfile='local.conf',
                debug=True)

    @foo.after_request
    def allow_cors(response):
        if 'cors_uri' in foo.config:
            response.headers['Access-Control-Allow-Origin'] = \
                foo.config['cors_uri']
        return response

    init_db(foo.config['database_uri'])

    if 'key_file' in foo.config and 'cert_file' in foo.config:
        import ssl
        verification = ssl.CERT_NONE
        ca_certs = None
        if 'ca_cert' in foo.config:
            ca_certs = [foo.config['ca_cert']]
            verification = ssl.CERT_OPTIONAL
        http_server = WSGIServer(
            (foo.config['bind_address'], int(foo.config['bind_port'])),
            foo,
            keyfile=foo.config['key_file'],
            certfile=foo.config['cert_file'],
            cert_reqs=verification,
            ca_certs=ca_certs)
    else:
        http_server = WSGIServer((foo.config['bind_address'],
                                  int(foo.config['bind_port'])), foo)
    http_server.serve_forever()
