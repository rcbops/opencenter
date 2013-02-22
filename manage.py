#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import sys

from migrate.versioning.shell import main

from opencenter.db.database import init_db
from opencenter.webapp import Thing

foo = Thing("opencenter", argv=sys.argv[1:], configfile='local.conf', debug=True)
init_db(foo.config['database_uri'])
# try multiple repo paths, for when devving locally versus package
for prefixes in ['/usr/share/pyshared', '.']:
    repo = os.path.join(*(prefixes.split('/') +
                          ['opencenter', 'db', 'migrate_repo']))
    if os.path.exists(repo):
        break

    repo = '/' + repo
    if os.path.exists(repo):
        break

if not os.path.exists(repo):
    print 'cannot find repo.'
    sys.exit(1)

main(url=foo.config['database_uri'], debug='True', repository=repo)
