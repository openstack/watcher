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
    PENDING = 'PENDING'
    ONGOING = 'ONGOING'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'
    DELETED = 'DELETED'
    CANCELLED = 'CANCELLED'


class Action(base.WatcherObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'action_plan_id': obj_utils.int_or_none,
        'action_type': obj_utils.str_or_none,
        'applies_to': obj_utils.str_or_none,
        'src': obj_utils.str_or_none,
        'dst': obj_utils.str_or_none,
        'parameter': obj_utils.str_or_none,
        'description': obj_utils.str_or_none,
        'state': obj_utils.str_or_none,
        'alarm': obj_utils.str_or_none,
        'next': obj_utils.int_or_none,
    }

    @staticmethod
    def _from_db_object(action, db_action):
        """Converts a database entity to a formal object."""
        for field in action.fields:
            action[field] = db_action[field]

        action.obj_reset_changes()
        return action

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return \
            [Action._from_db_object(cls(context), obj) for obj in db_objects]

    @classmethod
    def get(cls, context, action_id):
        """Find a action based on its id or uuid and return a Action object.

        :param action_id: the id *or* uuid of a action.
        :returns: a :class:`Action` object.
        """
        if utils.is_int_like(action_id):
            return cls.get_by_id(context, action_id)
        elif utils.is_uuid_like(action_id):
            return cls.get_by_uuid(context, action_id)
        else:
            raise exception.InvalidIdentity(identity=action_id)

    @classmethod
    def get_by_id(cls, context, action_id):
        """Find a action based on its integer id and return a Action object.

        :param action_id: the id of a action.
        :returns: a :class:`Action` object.
        """
        db_action = cls.dbapi.get_action_by_id(context, action_id)
        action = Action._from_db_object(cls(context), db_action)
        return action

    @classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a action based on uuid and return a :class:`Action` object.

        :param uuid: the uuid of a action.
        :param context: Security context
        :returns: a :class:`Action` object.
        """
        db_action = cls.dbapi.get_action_by_uuid(context, uuid)
        action = Action._from_db_object(cls(context), db_action)
        return action

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
        :returns: a list of :class:`Action` object.

        """
        db_actions = cls.dbapi.get_action_list(context,
                                               limit=limit,
                                               marker=marker,
                                               filters=filters,
                                               sort_key=sort_key,
                                               sort_dir=sort_dir)
        return Action._from_db_object_list(db_actions, cls, context)

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
        db_action = self.dbapi.create_action(values)
        self._from_db_object(self, db_action)

    def destroy(self, context=None):
        """Delete the Action from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Action(context)
        """
        self.dbapi.destroy_action(self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this Action.

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
        self.dbapi.update_action(self.uuid, updates)

        self.obj_reset_changes()

    def refresh(self, context=None):
        """Loads updates for this Action.

        Loads a action with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded action column by column, if there are any updates.

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
        """soft Delete the Audit from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        """
        self.dbapi.soft_delete_action(self.uuid)
        self.state = "DELETED"
        self.save()
