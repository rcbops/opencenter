#!/usr/bin/env python

import sys

from db.database import init_db
from webapp import Thing

if __name__ == '__main__':
    foo = Thing("roush", argv=sys.argv[1:], configfile='local.conf', debug=True)
    init_db(foo.config['database_uri'])
    foo.run()
