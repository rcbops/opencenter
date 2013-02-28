#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
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

from functools import partial


class DataType(object):
    Integer, String, JsonEntry, JsonBlob = range(0, 4)

    def __init__(self, data_type, data_size=0):
        self.data_type = data_type
        self.data_size = data_size

    def sqlalchemy_format(self):
        if self.data_type == self.Integer:
            return "INTEGER"
        elif self.data_type == self.JsonEntry:
            return "JSON_ENTRY"
        elif self.data_type == self.JsonBlob:
            return "JSON"
        elif self.data_type == self.String:
            return "VARCHAR(%s)" % self.data_size


# Make column types similar to sqlalchemy
Integer = DataType(DataType.Integer)
JsonEntry = DataType(DataType.JsonEntry)
JsonBlob = DataType(DataType.JsonBlob)
String = partial(DataType, DataType.String)


class Column(object):
    def __init__(self, column_type, *args, **kwargs):
        self.schema = {'primary_key': False,
                       'unique': False,
                       'updatable': True,
                       'required': False,
                       'read_only': False}
        self.schema.update(kwargs)
        self.schema['type'] = column_type.sqlalchemy_format()


class InMemoryBase(object):
    def __new__(cls, *args, **kwargs):
        obj = super(InMemoryBase, cls).__new__(cls, *args, **kwargs)

        if not '__cols__' in obj.__dict__:
            obj.__dict__['__cols__'] = {}

        for k, v in obj.__class__.__dict__.iteritems():
            if isinstance(v, Column):
                obj.__dict__['__cols__'][k] = v

        return obj

    def _coerce(self, what, towhat):
        if what is not None:
            return towhat(what)

        return what

    def __setattr__(self, name, value):
        if name in self.__dict__['__cols__']:
            wanted_type = None
            new_value = value

            type_name = self.__dict__['__cols__'][name].schema['type']

            if type_name == 'INTEGER' or type_name == 'NUMBER':
                wanted_type = int

            if 'VARCHAR' in type_name:
                wanted_type = str

            if wanted_type is not None:
                new_value = self._coerce(value, wanted_type)

            self.__dict__[name] = new_value
        else:
            self.__dict__[name] = value
