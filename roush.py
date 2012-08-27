#!/usr/bin/env python

from db.database import init_db
from webapp import Thing

if __name__ == '__main__':
    foo = Thing("roush", configfile='local.conf', debug=True)
    init_db(foo.config['database_uri'])
    foo.run()
