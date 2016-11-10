# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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
from watcher import objects
from watcher.objects import base
from watcher.objects import fields as wfields


@base.WatcherObjectRegistry.register
class Strategy(base.WatcherPersistentObject, base.WatcherObject,
               base.WatcherObjectDictCompat):

    # Version 1.0: Initial version
    # Version 1.1: Added Goal object field
    VERSION = '1.1'

    dbapi = db_api.get_instance()

    fields = {
        'id': wfields.IntegerField(),
        'uuid': wfields.UUIDField(),
        'name': wfields.StringField(),
        'display_name': wfields.StringField(),
        'goal_id': wfields.IntegerField(),
        'parameters_spec': wfields.FlexibleDictField(nullable=True),
        'goal': wfields.ObjectField('Goal', nullable=True),
    }

    object_fields = {'goal': (objects.Goal, 'goal_id')}

    @base.remotable_classmethod
    def get(cls, context, strategy_id, eager=False):
        """Find a strategy based on its id or uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param strategy_id: the id *or* uuid of a strategy.
        :param eager: Load object fields if True (Default: False)
        :returns: A :class:`Strategy` object.
        """
        if utils.is_int_like(strategy_id):
            return cls.get_by_id(context, strategy_id, eager=eager)
        elif utils.is_uuid_like(strategy_id):
            return cls.get_by_uuid(context, strategy_id, eager=eager)
        else:
            raise exception.InvalidIdentity(identity=strategy_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, strategy_id, eager=False):
        """Find a strategy based on its integer id

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param strategy_id: the id of a strategy.
        :param eager: Load object fields if True (Default: False)
        :returns: A :class:`Strategy` object.
        """
        db_strategy = cls.dbapi.get_strategy_by_id(
            context, strategy_id, eager=eager)
        strategy = cls._from_db_object(cls(context), db_strategy, eager=eager)
        return strategy

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, eager=False):
        """Find a strategy based on uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param uuid: the uuid of a strategy.
        :param eager: Load object fields if True (Default: False)
        :returns: A :class:`Strategy` object.
        """

        db_strategy = cls.dbapi.get_strategy_by_uuid(
            context, uuid, eager=eager)
        strategy = cls._from_db_object(cls(context), db_strategy, eager=eager)
        return strategy

    @base.remotable_classmethod
    def get_by_name(cls, context, name, eager=False):
        """Find a strategy based on name

        :param context: Security context
        :param name: the name of a strategy.
        :param eager: Load object fields if True (Default: False)
        :returns: A :class:`Strategy` object.
        """

        db_strategy = cls.dbapi.get_strategy_by_name(
            context, name, eager=eager)
        strategy = cls._from_db_object(cls(context), db_strategy, eager=eager)
        return strategy

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None, eager=False):
        """Return a list of :class:`Strategy` objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param filters: dict mapping the filter key to a value.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc`".
        :param eager: Load object fields if True (Default: False)
        :returns: a list of :class:`Strategy` object.
        """
        db_strategies = cls.dbapi.get_strategy_list(
            context,
            filters=filters,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)

        return [cls._from_db_object(cls(context), obj, eager=eager)
                for obj in db_strategies]

    @base.remotable
    def create(self, context=None):
        """Create a :class:`Strategy` record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :returns: A :class:`Strategy` object.
        """

        values = self.obj_get_changes()
        db_strategy = self.dbapi.create_strategy(values)
        # Note(v-francoise): Always load eagerly upon creation so we can send
        # notifications containing information about the related relationships
        self._from_db_object(self, db_strategy, eager=True)

    def destroy(self, context=None):
        """Delete the :class:`Strategy` from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        """
        self.dbapi.destroy_strategy(self.id)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this :class:`Strategy`.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_strategy(self.id, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None, eager=False):
        """Loads updates for this :class:`Strategy`.

        Loads a strategy with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded strategy column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param eager: Load object fields if True (Default: False)
        """
        current = self.__class__.get_by_id(
            self._context, strategy_id=self.id, eager=eager)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]

    @base.remotable
    def soft_delete(self, context=None):
        """Soft Delete the :class:`Strategy` from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        """
        self.dbapi.soft_delete_strategy(self.id)
