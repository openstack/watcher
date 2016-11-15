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
from watcher.db import api as db_api
from watcher.objects import base
from watcher.objects import fields as wfields


class ServiceStatus(object):
    ACTIVE = 'ACTIVE'
    FAILED = 'FAILED'


@base.WatcherObjectRegistry.register
class Service(base.WatcherPersistentObject, base.WatcherObject,
              base.WatcherObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': wfields.IntegerField(),
        'name': wfields.StringField(),
        'host': wfields.StringField(),
        'last_seen_up': wfields.DateTimeField(
            tzinfo_aware=False, nullable=True),
    }

    @base.remotable_classmethod
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

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a service based on name

        :param name: the name of a service.
        :param context: Security context
        :returns: a :class:`Service` object.
        """

        db_service = cls.dbapi.get_service_by_name(context, name)
        service = cls._from_db_object(cls(context), db_service)
        return service

    @base.remotable_classmethod
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

        return [cls._from_db_object(cls(context), obj) for obj in db_services]

    @base.remotable
    def create(self):
        """Create a :class:`Service` record in the DB."""
        values = self.obj_get_changes()
        db_service = self.dbapi.create_service(values)
        self._from_db_object(self, db_service)

    @base.remotable
    def save(self):
        """Save updates to this :class:`Service`.

        Updates will be made column by column based on the result
        of self.what_changed().
        """
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_service(self.id, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    def refresh(self):
        """Loads updates for this :class:`Service`.

        Loads a service with the same id from the database and
        checks for updated attributes. Updates are applied from
        the loaded service column by column, if there are any updates.
        """
        current = self.get(self._context, service_id=self.id)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]

    def soft_delete(self):
        """Soft Delete the :class:`Service` from the DB."""
        db_obj = self.dbapi.soft_delete_service(self.id)
        obj = self._from_db_object(
            self.__class__(self._context), db_obj, eager=False)
        self.obj_refresh(obj)
