#!/usr/bin/env python
import logging

import sqlalchemy

from roush.db.database import session
from roush.db import exceptions

from roush.webapp.ast import FilterBuilder, FilterTokenizer

LOG = logging.getLogger(__name__)


class DbAbstraction(object):
    def __init__(self):
        pass

    def get_columns(self):
        raise NotImplemented

    def get_all(self):
        raise NotImplemented

    def get_schema(self):
        raise NotImplemented

    def create(self, data):
        raise NotImplemented

    def delete(self, id):
        raise NotImplemented

    def get(self, id):
        raise NotImplemented

    def filter(self, filters):
        """get data by sql alchemy filters"""
        raise NotImplemented

    def query(self, query):
        """get data with filter language query"""
        raise NotImplemented

    def update(self, id, data):
        raise NotImplemented


class SqlAlchemyAbstraction(DbAbstraction):
    def __init__(self, model, name):
        self.model = model
        self.name = name

        super(SqlAlchemyAbstraction, self).__init__()

    def get_columns(self):
        field_list = [c for c in self.model.__table__.columns.keys()]
        if hasattr(self.model, '_synthesized_fields'):
            field_list += self.model._synthesized_fields

        return field_list

    def get_all(self):
        field_list = self.get_columns()

        return [dict((c, getattr(r, c))
                     for c in field_list)
                for r in self.model.query.all()]

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

        return {'schema': fields}

    def create(self, data):
        """Query helper for creating a row

        :param model: name of the table model
        :param fields: dict of columns:values to create
        """
        field_list = self.get_columns()
        field_list.remove('id')
        schema = self.get_schema()['schema']

        required_fields = [x for x in schema if schema[x]['required'] is True]
        ro_fields = [x for x in schema if schema[x]['read_only'] is True]

        if 'id' in required_fields:
            required_fields.remove('id')

        LOG.debug('Required fields for object %s: %s' % (self.name,
                                                         required_fields))

        for field in required_fields:
            if not field in data:
                raise KeyError('missing required field %s' % field)

        for field in ro_fields:
            if field in data:
                data.pop(field)

        r = self.model(**dict((field, data[field])
                              for field in field_list if field in data))

        session.add(r)
        try:
            session.commit()
            ret = dict((c, getattr(r, c))
                       for c in r.__table__.columns.keys())
            return ret
        except sqlalchemy.exc.StatementError as e:
            session.rollback()
            # msg = e.message
            msg = "JSON object must be either type(dict) or type(list) " \
                  "not %s" % (e.message)
            raise exceptions.CreateError(msg)
        except sqlalchemy.exc.IntegrityError as e:
            session.rollback()
            msg = "Unable to create %s, duplicate entry" % (self.name.title())
            raise exceptions.CreateError(message=msg)

    def delete(self, id):
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
        result = self.filter({'id': id})

        if len(result) == 0:
            return None

        return result[0]

    def filter(self, filters):
        """get data by sql alchemy filters"""
        filter_options = sqlalchemy.sql.and_(
            * [self.model.__table__.columns[k] == v
               for k, v in filters.iteritems()])
        r = self.model.query.filter(filter_options)
        if not r:
            result = None
        else:
            result = [dict((c, getattr(res, c))
                           for c in self.get_columns()) for res in r]
        return result

    def query(self, query):
        """get data with filter language query"""
        query = '%s: %s' % (self.name, query)

        builder = FilterBuilder(FilterTokenizer(), query)
        result = builder.filter()
        return result

    def update(self, id, data):
        field_list = [c for c in self.model.__table__.columns.keys()]

        r = self.model.query.filter_by(id=id).first()

        schema = self.get_schema()['schema']

        ro_fields = [x for x in schema if schema[x]['updatable'] is False]

        for field in ro_fields:
            if field in field_list:
                field_list.remove(field)

        for field in field_list:
            if field in data:
                r.__setattr__(field, data[field])
        try:
            ret = dict((c, getattr(r, c))
                       for c in r.__table__.columns.keys())
            session.commit()
            return ret
        except sqlalchemy.exc.InvalidRequestError as e:
            print "invalid req"
            session.rollback()
            msg = e.msg
            raise RuntimeError(msg)
        except:
            session.rollback()
            raise


class InMemoryAbstraction(DbAbstraction):
    pass
