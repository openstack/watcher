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


class Goal(base.WatcherObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'display_name': obj_utils.str_or_none,
        'efficacy_specification': obj_utils.list_or_none,
    }

    @staticmethod
    def _from_db_object(goal, db_goal):
        """Converts a database entity to a formal object."""
        for field in goal.fields:
            goal[field] = db_goal[field]

        goal.obj_reset_changes()
        return goal

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [cls._from_db_object(cls(context), obj) for obj in db_objects]

    @classmethod
    def get(cls, context, goal_id):
        """Find a goal based on its id or uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Goal(context)
        :param goal_id: the id *or* uuid of a goal.
        :returns: a :class:`Goal` object.
        """
        if utils.is_int_like(goal_id):
            return cls.get_by_id(context, goal_id)
        elif utils.is_uuid_like(goal_id):
            return cls.get_by_uuid(context, goal_id)
        else:
            raise exception.InvalidIdentity(identity=goal_id)

    @classmethod
    def get_by_id(cls, context, goal_id):
        """Find a goal based on its integer id

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Goal(context)
        :param goal_id: the id *or* uuid of a goal.
        :returns: a :class:`Goal` object.
        """
        db_goal = cls.dbapi.get_goal_by_id(context, goal_id)
        goal = cls._from_db_object(cls(context), db_goal)
        return goal

    @classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a goal based on uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Goal(context)
        :param uuid: the uuid of a goal.
        :returns: a :class:`Goal` object.
        """

        db_goal = cls.dbapi.get_goal_by_uuid(context, uuid)
        goal = cls._from_db_object(cls(context), db_goal)
        return goal

    @classmethod
    def get_by_name(cls, context, name):
        """Find a goal based on name

        :param name: the name of a goal.
        :param context: Security context
        :returns: a :class:`Goal` object.
        """

        db_goal = cls.dbapi.get_goal_by_name(context, name)
        goal = cls._from_db_object(cls(context), db_goal)
        return goal

    @classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None):
        """Return a list of :class:`Goal` objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Goal(context)
        :param filters: dict mapping the filter key to a value.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Goal` object.
        """
        db_goals = cls.dbapi.get_goal_list(
            context,
            filters=filters,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)
        return cls._from_db_object_list(db_goals, cls, context)

    def create(self):
        """Create a :class:`Goal` record in the DB."""

        values = self.obj_get_changes()
        db_goal = self.dbapi.create_goal(values)
        self._from_db_object(self, db_goal)

    def destroy(self):
        """Delete the :class:`Goal` from the DB."""
        self.dbapi.destroy_goal(self.id)
        self.obj_reset_changes()

    def save(self):
        """Save updates to this :class:`Goal`.

        Updates will be made column by column based on the result
        of self.what_changed().
        """
        updates = self.obj_get_changes()
        self.dbapi.update_goal(self.id, updates)

        self.obj_reset_changes()

    def refresh(self):
        """Loads updates for this :class:`Goal`.

        Loads a goal with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded goal column by column, if there are any updates.
        """
        current = self.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]

    def soft_delete(self):
        """Soft Delete the :class:`Goal` from the DB."""
        self.dbapi.soft_delete_goal(self.uuid)
