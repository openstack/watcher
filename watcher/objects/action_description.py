# -*- encoding: utf-8 -*-
# Copyright (c) 2017  ZTE
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


@base.WatcherObjectRegistry.register
class ActionDescription(base.WatcherPersistentObject, base.WatcherObject,
                        base.WatcherObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': wfields.IntegerField(),
        'action_type': wfields.StringField(),
        'description': wfields.StringField(),
    }

    @base.remotable_classmethod
    def get(cls, context, action_id):
        """Find a action description based on its id

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object
        :param action_id: the id of a action description.
        :returns: a :class:`ActionDescription` object.
        """
        if utils.is_int_like(action_id):
            db_action = cls.dbapi.get_action_description_by_id(
                context, action_id)
            action = ActionDescription._from_db_object(cls(context), db_action)
            return action
        else:
            raise exception.InvalidIdentity(identity=action_id)

    @base.remotable_classmethod
    def get_by_type(cls, context, action_type):
        """Find a action description based on action type

        :param action_type: the action type of a action description.
        :param context: Security context
        :returns: a :class:`ActionDescription` object.
        """

        db_action = cls.dbapi.get_action_description_by_type(
            context, action_type)
        action = cls._from_db_object(cls(context), db_action)
        return action

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None):
        """Return a list of :class:`ActionDescription` objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ActionDescription(context)
        :param filters: dict mapping the filter key to a value.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`ActionDescription` object.
        """
        db_actions = cls.dbapi.get_action_description_list(
            context,
            filters=filters,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)

        return [cls._from_db_object(cls(context), obj) for obj in db_actions]

    @base.remotable
    def create(self):
        """Create a :class:`ActionDescription` record in the DB."""
        values = self.obj_get_changes()
        db_action = self.dbapi.create_action_description(values)
        self._from_db_object(self, db_action)

    @base.remotable
    def save(self):
        """Save updates to this :class:`ActionDescription`.

        Updates will be made column by column based on the result
        of self.what_changed().
        """
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_action_description(self.id, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    def refresh(self):
        """Loads updates for this :class:`ActionDescription`.

        Loads a action description with the same id from the database and
        checks for updated attributes. Updates are applied from
        the loaded action description column by column, if there
        are any updates.
        """
        current = self.get(self._context, action_id=self.id)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]

    def soft_delete(self):
        """Soft Delete the :class:`ActionDescription` from the DB."""
        db_obj = self.dbapi.soft_delete_action_description(self.id)
        obj = self._from_db_object(
            self.__class__(self._context), db_obj, eager=False)
        self.obj_refresh(obj)
