#!/usr/bin/env python

import os
import sys

from migrate.versioning.shell import main

from roush.db.database import init_db
from roush.webapp import Thing

foo = Thing("roush", argv=sys.argv[1:], configfile='local.conf', debug=True)
init_db(foo.config['database_uri'])
# try multiple repo paths, for when devving locally versus package
for prefixes in ['/usr/share/pyshared', '.']:
    repo = os.path.join(*(prefixes.split('/') + ['roush', 'db', 'migrate_repo']))
    if os.path.exists(repo):
        break

    repo = '/' + repo
    if os.path.exists(repo):
        break

if not os.path.exists(repo):
    print 'cannot find repo.'
    sys.exit(1)

main(url=foo.config['database_uri'], debug='True', repository=repo)
