#!/usr/bin/env python
#               OpenCenter™ is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

import os
import sys

from migrate.versioning.shell import main

from opencenter.db.database import init_db
from opencenter.webapp import Thing

foo = Thing("opencenter",
            argv=sys.argv[1:],
            configfile='local.conf',
            debug=True)

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
