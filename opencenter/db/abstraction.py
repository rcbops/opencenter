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

import copy
import logging

import sqlalchemy

from opencenter.db.database import session
from opencenter.db import exceptions
from opencenter.db import inmemory

import opencenter.webapp.ast
# from opencenter.webapp.ast import FilterBuilder, FilterTokenizer


LOG = logging.getLogger(__name__)


class DbAbstraction(object):
    def __init__(self, api, model, name):
        classname = self.__class__.__name__.lower()
        self.logger = logging.getLogger('%s.%s' % (__name__, classname))
        self.api = api
        self.name = name
        self.model = model

    def destroy_cache(self):
        pass

    def get_columns(self):
        raise NotImplementedError

    def get_all(self):
        raise NotImplementedError

    def get_schema(self):
        raise NotImplementedError

    def create(self, data):
        raise NotImplementedError

    def delete(self, id):
        raise NotImplementedError

    def get(self, id):
        raise NotImplementedError

    def query(self, query):
        """get data with filter language query"""
        full_query = '%s: %s' % (self.name, query)

        builder = opencenter.webapp.ast.FilterBuilder(
            opencenter.webapp.ast.FilterTokenizer(),
            full_query, api=self.api)

        root = builder.build()

        # trivial optimization for a get_by_id
        if root.op == '=':
            if root.lhs.op == 'IDENTIFIER' and root.lhs.lhs == 'id':
                if root.rhs.op == 'NUMBER' or root.rhs.op == 'STRING':
                    return [self.get(int(root.rhs.lhs))]

        # not a straight get_by_id
        result = builder.filter()
        return result

    def update(self, id, data):
        raise NotImplementedError

    def first_by_query(self, query):
        result = self.query(query)
        if len(result):
            return result[0]
        return None

    # README(shep): this is not being called anywhere
    #def _coerce_data(self, data):
    #    schema = self.get_schema()
    #    for field, value in data.items():
    #        wanted_type = None
    #        type_name = None
    #        if field in schema:
    #            type_name = schema[field]['type']
    #        else:
    #            raise ValueError('non-schema data in update/create call')
    #        if type_name == 'INTEGER' or type_name == 'NUMBER':
    #            wanted_type = int
    #        if 'VARCHAR' in type_name:
    #            wanted_type = str
    #        if wanted_type is not None:
    #            data[field] = wanted_type(value)

    def _sanitize_for_update(self, data):
        # should we sanitize, or raise?
        retval = copy.deepcopy(data)

        # self._coerce_data(retval)

        schema = self.get_schema()

        ro_fields = [x for x in schema if schema[x]['updatable'] is False]

        for field in ro_fields:
            if field in retval:
                retval.pop(field)

        for field in data:
            if not field in schema.keys():
                retval.pop(field)

        return retval

    def _sanitize_for_create(self, data):
        retval = copy.deepcopy(data)

        # self._coerce_data(retval)

        schema = self.get_schema()

        required_fields = [x for x in schema if schema[x]['required'] is True]
        ro_fields = [x for x in schema if schema[x]['read_only'] is True]

        # this should be generalized to pks, I think?
        if 'id' in required_fields:
            required_fields.remove('id')

        if 'id' in retval:
            retval.pop('id')

        for field in required_fields:
            if not field in retval:
                raise KeyError('missing required field %s' % field)

        for field in ro_fields:
            if field in retval:
                retval.pop(field)

        for field in data:
            if not field in schema.keys():
                retval.pop(field)

        return retval

    def _validate_id_format(self, id_to_check):
        try:
            return int(id_to_check)
        except (TypeError, ValueError):
            msg = 'IdInvalid: id must be an integer.'
            raise exceptions.IdInvalid(message=msg)


class SqlAlchemyAbstraction(DbAbstraction):
    def __init__(self, api, model, name):
        super(SqlAlchemyAbstraction, self).__init__(api, model, name)

    def get_columns(self):
        field_list = [c for c in self.model.__table__.columns.keys()]
        if hasattr(self.model, '_synthesized_fields'):
            field_list += self.model._synthesized_fields

        return field_list

    def get_all(self):
        return [x.jsonify(api=self.api) for x in self.model.query.all()]

    def get_schema(self):
        obj = self.model
        cols = obj.__table__.columns

        fields = {}
        for k in cols.keys():
            fields[k] = {}
            fields[k]['type'] = str(cols[k].type)
            if repr(cols[k].type) == 'JsonBlob()':
                fields[k]['type'] = 'JSON'

            if repr(cols[k].type) == 'JsonEntry()':
                fields[k]['type'] = 'JSON_ENTRY'

            fields[k]['primary_key'] = cols[k].primary_key
            fields[k]['unique'] = cols[k].unique or cols[k].primary_key
            fields[k]['updatable'] = True
            fields[k]['required'] = not cols[k].nullable
            fields[k]['read_only'] = False

            if hasattr(obj, '_non_updatable_fields'):
                if k in obj._non_updatable_fields:
                    fields[k]['updatable'] = False

            if len(cols[k].foreign_keys) > 0:
                fields[k]['fk'] = list(cols[k].foreign_keys)[0].target_fullname

        if hasattr(obj, '_synthesized_fields'):
            for syn in obj._synthesized_fields:
                fields[syn] = {'type': 'TEXT',
                               'unique': False,
                               'required': False,
                               'updatable': False,
                               'read_only': True,
                               'primary_key': False}

        return fields

    def create(self, data):
        """Query helper for creating a row

        :param model: name of the table model
        :param fields: dict of columns:values to create
        """

        new_data = self._sanitize_for_create(data)

        if self.name in ('facts', 'attrs'):
            #checks that the node exists
            node = self.api._model_get_by_id('nodes', new_data['node_id'])

            query = 'node_id=%d and key="%s"' % (node['id'], new_data['key'])
            existing = self.api._model_query(self.name, query)
            if len(existing) != 0:
                return self.update(existing[0]['id'], data)

        r = self.model(**new_data)

        session.add(r)
        try:
            session.commit()
            return r.jsonify(api=self.api)
        except sqlalchemy.exc.IntegrityError as e:
            session.rollback()
            msg = "Unable to create %s, duplicate entry" % (self.name.title())
            raise exceptions.CreateError(msg)
        except sqlalchemy.exc.StatementError as e:
            session.rollback()
            # msg = e.message
            msg = "JSON object must be either type(dict) or type(list) " \
                  "not %s" % str(e)
            raise exceptions.CreateError(msg)

    def delete(self, id):
        id = self._validate_id_format(id)
        r = self.model.query.filter_by(id=id).first()
        # We need generate an object hash to pass to the backend notification

        try:
            session.delete(r)
            session.commit()
            return True
        except sqlalchemy.orm.exc.UnmappedInstanceError as e:
            session.rollback()
            msg = "%s id does not exist" % (self.name.title())
            raise exceptions.IdNotFound(message=msg)
        except sqlalchemy.exc.InvalidRequestError as e:
            session.rollback()
            msg = e.msg
            raise RuntimeError(msg)

    def get(self, id):
        id = self._validate_id_format(id)
        r = self.model.query.filter_by(id=id).first()

        if not r:
            msg = '%s id %d does not exist' % (self.name.title(), id)
            raise exceptions.IdNotFound(message=msg)

        return r.jsonify(api=self.api)

    def update(self, id, data):
        id = self._validate_id_format(id)

        new_data = self._sanitize_for_update(data)
        r = self.model.query.filter_by(id=id).first()

        for field in new_data:
            r.__setattr__(field, data[field])

        try:
            ret = r.jsonify(api=self.api)
            session.commit()
            return ret
        except sqlalchemy.exc.InvalidRequestError as e:
            session.rollback()
            msg = e.msg
            raise RuntimeError(msg)
        except:
            session.rollback()
            raise

    def _ast_to_sqlalchemy(self, ast):
        if ast.op == 'AND':
            return sqlalchemy.and_(self._ast_to_sqlalchemy(ast.lhs),
                                   self._ast_to_sqlalchemy(ast.rhs))

        if ast.op == 'OR':
            return sqlalchemy.or_(self._ast_to_sqlalchemy(ast.lhs),
                                  self._ast_to_sqlalchemy(ast.rhs))

        if ast.op == '=' and ast.lhs.op == 'IDENTIFIER' and ast.rhs.op in \
                ['STRING', 'NUMBER']:
            return self.model.__table__.columns[ast.lhs.lhs] == ast.rhs.lhs

        raise ValueError('Cannot convert to sqlalchemy query')

    def query(self, query):
        """
        try and optimize the ast query into a sql query, leveraging the
        ast node sql() method
        """

        full_query = '%s: %s' % (self.name, query)
        builder = opencenter.webapp.ast.FilterBuilder(
            opencenter.webapp.ast.FilterTokenizer(),
            full_query, api=self.api)

        root = builder.build()

        sql_filter = None

        try:
            sql_filter = self._ast_to_sqlalchemy(root)
        except ValueError:
            self.logger.error('could not convert %s to native sql' % (query))

        if sql_filter is not None:
            r = self.model.query.filter(sql_filter)
            if not r:
                return None
            else:
                return [x.jsonify(api=self.api) for x in r]

        return builder.filter()


class APIAbstraction(DbAbstraction):
    # same interface, but we'll pull the data from the
    # actual api.
    def __init__(self, api, model, name, endpoint):
        self.endpoint = endpoint
        self.schema = None
        self.objects = endpoint[name]
        super(APIAbstraction, self).__init__(api, model, name)

    def get_columns(self):
        if self.schema is None:
            self.schema = self.get_schema()

        return self.schema.keys()

    def get_all(self):
        self.objects._refresh(True)
        for obj in self.objects:
            yield obj.to_hash()

    def get_schema(self):
        self.objects._maybe_refresh_schema()
        return self.objects.schema.field_schema

    def create(self, data):
        new_data = self._sanitize_for_create(data)
        new_node = self.objects.new(**new_data)
        new_node.save()
        return new_node.to_hash()

    def delete(self, id):
        id = self._validate_id_format(id)

        try:
            obj = self.objects[id]
            obj.delete()
        except KeyError:
            raise exceptions.IdNotFound(message='id %d does not exist' % id)
        except ValueError:
            raise exceptions.IdNotFound(message='id %d does not exist' % id)

    def get(self, id):
        # This sort of naively assumes that the id
        # is an integer.  That's probably mostly right though.
        id = self._validate_id_format(id)

        try:
            obj = self.objects[id]

            if obj is None:
                self.objects._refresh(True)

            obj = self.objects[id]
            if obj is not None:
                obj._request('get')

            json_object = self.objects[id].to_hash()
        except KeyError:
            return None

        return json_object

    def update(self, id, data):
        id = self._validate_id_format(id)

        new_data = self._sanitize_for_update(data)

        try:
            obj = self.objects[id]
        except KeyError:
            raise exceptions.IdNotFound(message='id %d does not exist' % id)

        obj = self.objects.new(id=id, **(self._sanitize_for_update(new_data)))
        obj.save()

        return obj.to_hash()


class InMemoryAbstraction(DbAbstraction):
    # with the in-memory abstraction, we pass a dict that is
    # implemented in keys.  We'll still use the model table to
    # describe metadata, though.
    def __init__(self, api, model, name, dictionary):
        self.dictionary = dictionary
        self.model = model

        super(InMemoryAbstraction, self).__init__(api, model, name)

    def get_columns(self):
        cols = []

        for attr in dir(self.model):
            if isinstance(getattr(self.model, attr), inmemory.Column):
                cols.append(attr)

        if hasattr(self.model, '_synthesized_fields'):
            cols += self.model._synthesized_fields

        return cols

    def get_all(self):
        return self.dictionary.values()

    def get_schema(self):
        fields = {}

        for attr in dir(self.model):
            col = getattr(self.model, attr)

            if isinstance(getattr(self.model, attr), inmemory.Column):
                fields[attr] = col.schema

        if hasattr(self.model, '_synthesized_fields'):
            for syn in self.model._synthesized_fields:
                fields[syn] = {'type': 'TEXT',
                               'unique': False,
                               'required': False,
                               'updatable': False,
                               'read_only': True,
                               'primary_key': False}

        return fields

    def create(self, data):
        new_data = self._sanitize_for_create(data)

        try:
            new_thing = self.model(**new_data)
        except TypeError:
            raise exceptions.CreateError('bad data type')

        retval = new_thing.jsonify(api=self.api)
        retval['id'] = self._get_new_id()

        self.dictionary[retval['id']] = retval
        return retval

    def delete(self, id):
        id = self._validate_id_format(id)

        if not id in self.dictionary:
            raise exceptions.IdNotFound(message='id %d does not exist' % id)

        self.dictionary.pop(id)
        return True

    def get(self, id):
        # This sort of naively assumes that the id
        # is an integer.  That's probably mostly right though.
        id = self._validate_id_format(id)

        if id in self.dictionary:
            return self.dictionary[id]
        return None

    def update(self, id, data):
        id = self._validate_id_format(id)

        new_data = self._sanitize_for_update(data)
        self.dictionary[id].update(new_data)
        return self.dictionary[id]

    def _get_new_id(self):
        if len(self.dictionary) == 0:
            return 1
        return max(self.dictionary.keys()) + 1


class CachedAbstraction(DbAbstraction):
    def __init__(self, api, model, name, base_abstraction):
        self.cache = None
        self.base = base_abstraction

        super(CachedAbstraction, self).__init__(api, model, name)

    def destroy_cache(self):
        self.base.destroy_cache()
        self.cache = None

    def get_columns(self):
        return self.base.get_columns()

    def get_all(self):
        if self.cache is None:
            self.cache = {}

            for obj in self.base.get_all():
                self.cache[int(obj['id'])] = obj

        return self.cache.values()

    def get_schema(self):
        return self.base.get_schema()

    def create(self, data):
        result = self.base.create(data)
        self.api.destroy_cache()
        return result

    def delete(self, data):
        result = self.base.delete(data)
        self.api.destroy_cache()
        return result

    def get(self, id):
        id = self._validate_id_format(id)

        if self.cache is None:
            return self.base.get(id)
        else:
            if not id in self.cache:
                raise exceptions.IdNotFound(
                    message='%s id %d does not exist' % (self.model, int(id)))
            else:
                return self.cache[int(id)]

    def update(self, id, data):
        id = self._validate_id_format(id)
        result = self.base.update(id, data)
        self.api.destroy_cache()
        return result

    # def filter(self, filters):
    #     return self.base.filter(filters)


class EphemeralAbstraction(DbAbstraction):
    def __init__(self, api, model, name, base_abstraction):
        self.del_obj = []
        self.new_obj = {}
        self.upd_obj = {}
        self.current_max = 100000000

        self.base = base_abstraction

        super(EphemeralAbstraction, self).__init__(api, model, name)

    def transactions(self):
        result = {}
        if len(self.del_obj) > 0:
            result['deleted'] = self.del_obj
        if len(self.new_obj) > 0:
            result['new'] = self.new_obj
        if len(self.upd_obj) > 0:
            result['updated'] = self.upd_obj
        if result == {}:
            return None
        return result

    def _update_object(self, underlying):
        if underlying['id'] in self.del_obj:
            return None

        if not underlying['id'] in self.upd_obj:
            return underlying

        updated_object = copy.deepcopy(underlying)
        updated_object.update(self.upd_obj[underlying['id']])
        return updated_object

    def get_columns(self):
        return self.base.get_columns()

    def get_all(self):
        result = []

        for obj in self.base.get_all():
            new_obj = self._update_object(obj)
            if new_obj is not None:
                r = self.model(**(self._sanitize_for_create(new_obj)))
                r.id = new_obj['id']
                new_obj = r.jsonify(api=self.api)
                result.append(new_obj)

        for id, obj in self.new_obj.items():
            new_obj = self._update_object(obj)
            if new_obj is not None:
                result.append(new_obj)

        return result

    def get_schema(self):
        return self.base.get_schema()

    def create(self, data):
        # this is totally wrong.  we need to
        # fix up this data model
        new_data = self._sanitize_for_create(data)

        if self.name == 'facts':
            existing = self.api._model_query(
                'facts', 'node_id=%d and key="%s"' % (
                    int(new_data['node_id']), new_data['key']))
            if len(existing) != 0:
                # this is an update
                return self.update(existing[0]['id'], data)

        new_data['id'] = self._get_new_id()

        self.new_obj[new_data['id']] = new_data
        return new_data

    def delete(self, id):
        id = self._validate_id_format(id)

        if id in self.del_obj:
            raise exceptions.IdNotFound(message='id %d does not exist' % id)

        obj = self.base.get(id)
        if obj is None:
            raise exceptions.IdNotFound(message='id %d does not exist' % id)

        self.del_obj.append(id)
        return True

    def get(self, id):
        id = self._validate_id_format(id)

        new_obj = None

        obj = self.base.get(id)
        if obj is not None:
            new_obj = self._update_object(obj)
        else:
            # maybe newly created thing
            if id in self.new_obj:
                new_obj = self.new_obj[id]

        if new_obj is None:
            raise exceptions.IdNotFound(message='id %d does not exist' % id)

        r = self.model(**(self._sanitize_for_create(new_obj)))
        r.id = id

        result = r.jsonify(api=self.api)
        return result

    def update(self, id, data):
        id = self._validate_id_format(id)
        new_data = self._sanitize_for_update(data)

        if id in self.del_obj:
            raise exceptions.IdNotFound(message='%s id %d does not exist' %
                                        (self.model, id))

        obj = None

        try:
            obj = self.base.get(id)
        except exceptions.IdNotFound:
            if id in self.new_obj:
                obj = self.new_obj[id]

        if not obj:
            raise exceptions.IdNotFound(message='%s id %d does not exist' %
                                        (self.model, id))

        existing_obj = self._update_object(obj)

        if not id in self.upd_obj:
            self.upd_obj[id] = {}

        for field in new_data:
            if existing_obj[field] != new_data[field]:
                self.upd_obj[id][field] = new_data[field]

        new_obj = self._update_object(existing_obj)
        return new_obj

    def _get_new_id(self):
        # FIXME: race
        self.current_max += 1
        return self.current_max
