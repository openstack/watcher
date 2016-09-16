# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from watcher.common import exception
from watcher.common import utils
from watcher.db import api as dbapi
from watcher.objects import base
from watcher.objects import utils as obj_utils


class ServiceStatus(object):
    ACTIVE = 'ACTIVE'
    FAILED = 'FAILED'


class Service(base.WatcherObject):

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'name': obj_utils.str_or_none,
        'host': obj_utils.str_or_none,
        'last_seen_up': obj_utils.datetime_or_str_or_none
    }

    @staticmethod
    def _from_db_object(service, db_service):
        """Converts a database entity to a formal object."""
        for field in service.fields:
            service[field] = db_service[field]

        service.obj_reset_changes()
        return service

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Service._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def get(cls, context, service_id):
        """Find a service based on its id

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        :param service_id: the id of a service.
        :returns: a :class:`Service` object.
        """
        if utils.is_int_like(service_id):
            db_service = cls.dbapi.get_service_by_id(context, service_id)
            service = Service._from_db_object(cls(context), db_service)
            return service
        else:
            raise exception.InvalidIdentity(identity=service_id)

    @classmethod
    def get_by_name(cls, context, name):
        """Find a service based on name

        :param name: the name of a service.
        :param context: Security context
        :returns: a :class:`Service` object.
        """

        db_service = cls.dbapi.get_service_by_name(context, name)
        service = cls._from_db_object(cls(context), db_service)
        return service

    @classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None):
        """Return a list of :class:`Service` objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        :param filters: dict mapping the filter key to a value.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Service` object.
        """
        db_services = cls.dbapi.get_service_list(
            context,
            filters=filters,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)
        return Service._from_db_object_list(db_services, cls, context)

    def create(self, context=None):
        """Create a :class:`Service` record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """

        values = self.obj_get_changes()
        db_service = self.dbapi.create_service(values)
        self._from_db_object(self, db_service)

    def save(self, context=None):
        """Save updates to this :class:`Service`.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_service(self.id, updates)

        self.obj_reset_changes()

    def refresh(self, context=None):
        """Loads updates for this :class:`Service`.

        Loads a service with the same id from the database and
        checks for updated attributes. Updates are applied from
        the loaded service column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        current = self.__class__.get(self._context, service_id=self.id)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]

    def soft_delete(self, context=None):
        """Soft Delete the :class:`Service` from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        self.dbapi.soft_delete_service(self.id)
