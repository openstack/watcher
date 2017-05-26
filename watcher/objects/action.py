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
from watcher.db import api as db_api
from watcher import notifications
from watcher import objects
from watcher.objects import base
from watcher.objects import fields as wfields


class State(object):
    PENDING = 'PENDING'
    ONGOING = 'ONGOING'
    FAILED = 'FAILED'
    SUCCEEDED = 'SUCCEEDED'
    DELETED = 'DELETED'
    CANCELLED = 'CANCELLED'
    CANCELLING = 'CANCELLING'


@base.WatcherObjectRegistry.register
class Action(base.WatcherPersistentObject, base.WatcherObject,
             base.WatcherObjectDictCompat):

    # Version 1.0: Initial version
    # Version 1.1: Added 'action_plan' object field
    # Version 2.0: Removed 'next' object field, Added 'parents' object field
    VERSION = '2.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': wfields.IntegerField(),
        'uuid': wfields.UUIDField(),
        'action_plan_id': wfields.IntegerField(),
        'action_type': wfields.StringField(nullable=True),
        'input_parameters': wfields.DictField(nullable=True),
        'state': wfields.StringField(nullable=True),
        'parents': wfields.ListOfStringsField(nullable=True),

        'action_plan': wfields.ObjectField('ActionPlan', nullable=True),
    }
    object_fields = {
        'action_plan': (objects.ActionPlan, 'action_plan_id'),
    }

    @base.remotable_classmethod
    def get(cls, context, action_id, eager=False):
        """Find a action based on its id or uuid and return a Action object.

        :param action_id: the id *or* uuid of a action.
        :param eager: Load object fields if True (Default: False)
        :returns: a :class:`Action` object.
        """
        if utils.is_int_like(action_id):
            return cls.get_by_id(context, action_id, eager=eager)
        elif utils.is_uuid_like(action_id):
            return cls.get_by_uuid(context, action_id, eager=eager)
        else:
            raise exception.InvalidIdentity(identity=action_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, action_id, eager=False):
        """Find a action based on its integer id and return a Action object.

        :param action_id: the id of a action.
        :param eager: Load object fields if True (Default: False)
        :returns: a :class:`Action` object.
        """
        db_action = cls.dbapi.get_action_by_id(context, action_id, eager=eager)
        action = cls._from_db_object(cls(context), db_action, eager=eager)
        return action

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, eager=False):
        """Find a action based on uuid and return a :class:`Action` object.

        :param uuid: the uuid of a action.
        :param context: Security context
        :param eager: Load object fields if True (Default: False)
        :returns: a :class:`Action` object.
        """
        db_action = cls.dbapi.get_action_by_uuid(context, uuid, eager=eager)
        action = cls._from_db_object(cls(context), db_action, eager=eager)
        return action

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None, eager=False):
        """Return a list of Action objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param filters: Filters to apply. Defaults to None.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param eager: Load object fields if True (Default: False)
        :returns: a list of :class:`Action` object.
        """
        db_actions = cls.dbapi.get_action_list(context,
                                               limit=limit,
                                               marker=marker,
                                               filters=filters,
                                               sort_key=sort_key,
                                               sort_dir=sort_dir,
                                               eager=eager)

        return [cls._from_db_object(cls(context), obj, eager=eager)
                for obj in db_actions]

    @base.remotable
    def create(self):
        """Create an :class:`Action` record in the DB.

        :returns: An :class:`Action` object.
        """
        values = self.obj_get_changes()
        db_action = self.dbapi.create_action(values)
        # Note(v-francoise): Always load eagerly upon creation so we can send
        # notifications containing information about the related relationships
        self._from_db_object(self, db_action, eager=True)

        notifications.action.send_create(self.obj_context, self)

    def destroy(self):
        """Delete the Action from the DB"""
        self.dbapi.destroy_action(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self):
        """Save updates to this Action.

        Updates will be made column by column based on the result
        of self.what_changed().
        """
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_action(self.uuid, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        notifications.action.send_update(self.obj_context, self)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, eager=False):
        """Loads updates for this Action.

        Loads a action with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded action column by column, if there are any updates.
        :param eager: Load object fields if True (Default: False)
        """
        current = self.get_by_uuid(self._context, uuid=self.uuid, eager=eager)
        self.obj_refresh(current)

    @base.remotable
    def soft_delete(self):
        """Soft Delete the Audit from the DB"""
        self.state = State.DELETED
        self.save()
        db_obj = self.dbapi.soft_delete_action(self.uuid)
        obj = self._from_db_object(
            self.__class__(self._context), db_obj, eager=False)
        self.obj_refresh(obj)

        notifications.action.send_delete(self.obj_context, self)
