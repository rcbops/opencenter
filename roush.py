#!/usr/bin/env python

import sys

from gevent.wsgi import WSGIServer

from db.database import init_db
from webapp import Thing

if __name__ == '__main__':
    foo = Thing("roush", argv=sys.argv[1:], configfile='local.conf',
                debug=True)

    @foo.after_request
    def allow_cors(response):
        if foo.config.has_key('cors_uri'):
            response.headers['Access-Control-Allow-Origin'] = \
                foo.config['cors_uri']
        return response

    init_db(foo.config['database_uri'])

    http_server = WSGIServer((foo.config['bind_address'],
                              int(foo.config['bind_port'])), foo)
    http_server.serve_forever()
