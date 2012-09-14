#!/usr/bin/env python

import sys

from migrate.versioning.shell import main

from db.database import init_db
from webapp import Thing

foo = Thing("roush", argv=sys.argv[1:], configfile='local.conf', debug=True)
init_db(foo.config['database_uri'])
main(url=foo.config['database_uri'], debug='True',
     repository='db/migrate_repo/')
