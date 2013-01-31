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
