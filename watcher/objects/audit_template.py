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


from oslo_config import cfg
from watcher.common import exception
from watcher.common import utils
from watcher.db import api as dbapi
from watcher.objects import base
from watcher.objects import utils as obj_utils


class Goal(object):
    SERVERS_CONSOLIDATION = 'SERVERS_CONSOLIDATION'
    MINIMIZE_ENERGY_CONSUMPTION = 'MINIMIZE_ENERGY_CONSUMPTION'
    BALANCE_LOAD = 'BALANCE_LOAD'
    MINIMIZE_LICENSING_COST = 'MINIMIZE_LICENSING_COST'
    PREPARE_PLANNED_OPERATION = 'PREPARE_PLANNED_OPERATION'


class AuditTemplate(base.WatcherObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'description': obj_utils.str_or_none,
        'goal': obj_utils.str_or_none,
        'host_aggregate': obj_utils.int_or_none,
        'extra': obj_utils.dict_or_none,
        'version': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(audit_template, db_audit_template):
        """Converts a database entity to a formal object."""
        for field in audit_template.fields:
            audit_template[field] = db_audit_template[field]

        audit_template.obj_reset_changes()
        return audit_template

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return \
            [AuditTemplate._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def get(cls, context, audit_template_id):
        """Find a audit template based on its id or uuid and return an
            :class:`AuditTemplate` object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        :param audit_template_id: the id *or* uuid of a audit_template.
        :returns: a :class:`AuditTemplate` object.
        """

        if utils.is_int_like(audit_template_id):
            return cls.get_by_id(context, audit_template_id)
        elif utils.is_uuid_like(audit_template_id):
            return cls.get_by_uuid(context, audit_template_id)
        else:
            raise exception.InvalidIdentity(identity=audit_template_id)

    @classmethod
    def get_by_id(cls, context, audit_template_id):
        """Find an audit template based on its integer id and return a
            :class:`AuditTemplate` object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        :param audit_template_id: the id of a audit_template.
        :returns: a :class:`AuditTemplate` object.
        """

        db_audit_template = cls.dbapi.get_audit_template_by_id(
            context,
            audit_template_id)
        audit_template = AuditTemplate._from_db_object(cls(context),
                                                       db_audit_template)
        return audit_template

    @classmethod
    def get_by_uuid(cls, context, uuid):
        """Find an audit template based on uuid and return a
            :class:`AuditTemplate` object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        :param uuid: the uuid of a audit_template.
        :returns: a :class:`AuditTemplate` object.
        """

        db_audit_template = cls.dbapi.get_audit_template_by_uuid(context, uuid)
        audit_template = AuditTemplate._from_db_object(cls(context),
                                                       db_audit_template)
        return audit_template

    @classmethod
    def get_by_name(cls, context, name):
        """Find an audit template based on name and return a
            :class:`AuditTemplate` object.

        :param name: the logical name of a audit_template.
        :param context: Security context
        :returns: a :class:`AuditTemplate` object.
        """
        db_audit_template = cls.dbapi.get_audit_template_by_name(context, name)
        audit_template = AuditTemplate._from_db_object(cls(context),
                                                       db_audit_template)
        return audit_template

    @classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of :class:`AuditTemplate` objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`AuditTemplate` object.
        """

        db_audit_templates = cls.dbapi.get_audit_template_list(
            context,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)
        return AuditTemplate._from_db_object_list(db_audit_templates,
                                                  cls, context)

    def create(self, context=None):
        """Create a :class:`AuditTemplate` record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)

        """
        values = self.obj_get_changes()
        goal = values['goal']
        if goal not in cfg.CONF.watcher_goals.goals.keys():
            raise exception.InvalidGoal(goal=goal)
        db_audit_template = self.dbapi.create_audit_template(values)
        self._from_db_object(self, db_audit_template)

    def destroy(self, context=None):
        """Delete the :class:`AuditTemplate` from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        """
        self.dbapi.destroy_audit_template(self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this :class:`AuditTemplate`.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_audit_template(self.uuid, updates)

        self.obj_reset_changes()

    def refresh(self, context=None):
        """Loads updates for this :class:`AuditTemplate`.

        Loads a audit_template with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded audit_template column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                    self[field] = current[field]

    def soft_delete(self, context=None):
        """soft Delete the :class:`AuditTemplate` from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: AuditTemplate(context)
        """
        self.dbapi.soft_delete_audit_template(self.uuid)
