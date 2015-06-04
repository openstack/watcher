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


class Status(object):
    RECOMMENDED = 'RECOMMENDED'
    ONGOING = 'ONGOING'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'
    DELETED = 'DELETED'
    CANCELLED = 'CANCELLED'


class ActionPlan(base.WatcherObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'audit_id': obj_utils.int_or_none,
        'first_action_id': obj_utils.int_or_none,
        'state': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(action_plan, db_action_plan):
        """Converts a database entity to a formal object."""
        for field in action_plan.fields:
            action_plan[field] = db_action_plan[field]

        action_plan.obj_reset_changes()
        return action_plan

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ActionPlan._from_db_object(
            cls(context), obj) for obj in db_objects]

    @classmethod
    def get(cls, context, action_plan_id):
        """Find a action_plan based on its id or uuid and return a Action object.

        :param action_plan_id: the id *or* uuid of a action_plan.
        :returns: a :class:`Action` object.
        """
        if utils.is_int_like(action_plan_id):
            return cls.get_by_id(context, action_plan_id)
        elif utils.is_uuid_like(action_plan_id):
            return cls.get_by_uuid(context, action_plan_id)
        else:
            raise exception.InvalidIdentity(identity=action_plan_id)

    @classmethod
    def get_by_id(cls, context, action_plan_id):
        """Find a action_plan based on its integer id and return a Action object.

        :param action_plan_id: the id of a action_plan.
        :returns: a :class:`Action` object.
        """
        db_action_plan = cls.dbapi.get_action_plan_by_id(
            context, action_plan_id)
        action_plan = ActionPlan._from_db_object(
            cls(context), db_action_plan)
        return action_plan

    @classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a action_plan based on uuid and return a :class:`Action` object.

        :param uuid: the uuid of a action_plan.
        :param context: Security context
        :returns: a :class:`Action` object.
        """
        db_action_plan = cls.dbapi.get_action_plan_by_uuid(context, uuid)
        action_plan = ActionPlan._from_db_object(cls(context), db_action_plan)
        return action_plan

    @classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None):
        """Return a list of Action objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param filters: Filters to apply. Defaults to None.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`ActionPlan` object.

        """
        db_action_plans = cls.dbapi.get_action_plan_list(context,
                                                         limit=limit,
                                                         marker=marker,
                                                         filters=filters,
                                                         sort_key=sort_key,
                                                         sort_dir=sort_dir)
        return ActionPlan._from_db_object_list(db_action_plans, cls, context)

    def create(self, context=None):
        """Create a Action record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Action(context)

        """
        values = self.obj_get_changes()
        db_action_plan = self.dbapi.create_action_plan(values)
        self._from_db_object(self, db_action_plan)

    def destroy(self, context=None):
        """Delete the Action from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Action(context)
        """
        self.dbapi.destroy_action_plan(self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this Action plan.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Action(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_action_plan(self.uuid, updates)

        self.obj_reset_changes()

    def refresh(self, context=None):
        """Loads updates for this Action plan.

        Loads a action_plan with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded action_plan column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Action(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                    self[field] = current[field]

    def soft_delete(self, context=None):
        """soft Delete the Action plan from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        """
        self.dbapi.soft_delete_action_plan(self.uuid)
        self.state = "DELETED"
        self.save()
