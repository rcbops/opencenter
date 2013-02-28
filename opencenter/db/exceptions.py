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


class NodeNotFound(Exception):
    message = "Node not found"

    def __init__(self, message=message):
        self.message = message


class CreateError(Exception):
    message = "Generic unable to create error"

    def __init__(self, message=message):
        self.message = message


class AdventureNotFound(Exception):
    message = "Adventure not found"

    def __init__(self, message=message):
        self.message = message


class IdNotFound(Exception):
    message = "Object Not Found"

    def __init__(self, message=message):
        self.message = message
