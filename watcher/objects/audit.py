# -*- encoding: utf-8 -*-
# Copyright 2013 IBM Corp.
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


class AuditStatus(object):
    ONGOING = 'ONGOING'
    SUCCESS = 'SUCCESS'
    SUBMITTED = 'SUBMITTED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    DELETED = 'DELETED'
    PENDING = 'PENDING'


class AuditType(object):
    ONESHOT = 'ONESHOT'
    CONTINUOUS = 'CONTINUOUS'


class Audit(base.WatcherObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'type': obj_utils.str_or_none,
        'state': obj_utils.str_or_none,
        'deadline': obj_utils.datetime_or_str_or_none,
        'audit_template_id': obj_utils.int_or_none,
    }

    @staticmethod
    def _from_db_object(audit, db_audit):
        """Converts a database entity to a formal object."""
        for field in audit.fields:
            audit[field] = db_audit[field]

        audit.obj_reset_changes()
        return audit

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return \
            [Audit._from_db_object(cls(context), obj) for obj in db_objects]

    @classmethod
    def get(cls, context, audit_id):
        """Find a audit based on its id or uuid and return a Audit object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param audit_id: the id *or* uuid of a audit.
        :returns: a :class:`Audit` object.
        """
        if utils.is_int_like(audit_id):
            return cls.get_by_id(context, audit_id)
        elif utils.is_uuid_like(audit_id):
            return cls.get_by_uuid(context, audit_id)
        else:
            raise exception.InvalidIdentity(identity=audit_id)

    @classmethod
    def get_by_id(cls, context, audit_id):
        """Find a audit based on its integer id and return a Audit object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param audit_id: the id of a audit.
        :returns: a :class:`Audit` object.
        """
        db_audit = cls.dbapi.get_audit_by_id(context, audit_id)
        audit = Audit._from_db_object(cls(context), db_audit)
        return audit

    @classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a audit based on uuid and return a :class:`Audit` object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param uuid: the uuid of a audit.
        :returns: a :class:`Audit` object.
        """

        db_audit = cls.dbapi.get_audit_by_uuid(context, uuid)
        audit = Audit._from_db_object(cls(context), db_audit)
        return audit

    @classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None):
        """Return a list of Audit objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param filters: Filters to apply. Defaults to None.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Audit` object.

        """
        db_audits = cls.dbapi.get_audit_list(context,
                                             limit=limit,
                                             marker=marker,
                                             filters=filters,
                                             sort_key=sort_key,
                                             sort_dir=sort_dir)
        return Audit._from_db_object_list(db_audits, cls, context)

    def create(self, context=None):
        """Create a Audit record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)

        """
        values = self.obj_get_changes()
        db_audit = self.dbapi.create_audit(values)
        self._from_db_object(self, db_audit)

    def destroy(self, context=None):
        """Delete the Audit from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        """
        self.dbapi.destroy_audit(self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this Audit.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_audit(self.uuid, updates)

        self.obj_reset_changes()

    def refresh(self, context=None):
        """Loads updates for this Audit.

        Loads a audit with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded audit column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                    self[field] = current[field]

    def soft_delete(self, context=None):
        """soft Delete the Audit from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        """
        self.dbapi.soft_delete_audit(self.uuid)
        self.state = "DELETED"
        self.save()
