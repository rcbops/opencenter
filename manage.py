#!/usr/bin/env python

import os
import sys

from migrate.versioning.shell import main

from roush.db.database import init_db
from roush.webapp import Thing

foo = Thing("roush", argv=sys.argv[1:], configfile='local.conf', debug=True)
init_db(foo.config['database_uri'])
repo = os.path.join(os.path.dirname(__file__), 'roush', 'db', 'migrate_repo')
main(url=foo.config['database_uri'], debug='True', repository=repo)
