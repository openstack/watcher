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
from watcher.db import api as dbapi
from watcher.objects import base
from watcher.objects import utils as obj_utils


class Strategy(base.WatcherObject):

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'display_name': obj_utils.str_or_none,
        'goal_id': obj_utils.int_or_none,
        'parameters_spec': obj_utils.dict_or_none,
    }

    @staticmethod
    def _from_db_object(strategy, db_strategy):
        """Converts a database entity to a formal object."""
        for field in strategy.fields:
            strategy[field] = db_strategy[field]

        strategy.obj_reset_changes()
        return strategy

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Strategy._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def get(cls, context, strategy_id):
        """Find a strategy based on its id or uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param strategy_id: the id *or* uuid of a strategy.
        :returns: a :class:`Strategy` object.
        """
        if utils.is_int_like(strategy_id):
            return cls.get_by_id(context, strategy_id)
        elif utils.is_uuid_like(strategy_id):
            return cls.get_by_uuid(context, strategy_id)
        else:
            raise exception.InvalidIdentity(identity=strategy_id)

    @classmethod
    def get_by_id(cls, context, strategy_id):
        """Find a strategy based on its integer id

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param strategy_id: the id of a strategy.
        :returns: a :class:`Strategy` object.
        """
        db_strategy = cls.dbapi.get_strategy_by_id(context, strategy_id)
        strategy = Strategy._from_db_object(cls(context), db_strategy)
        return strategy

    @classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a strategy based on uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param uuid: the uuid of a strategy.
        :returns: a :class:`Strategy` object.
        """

        db_strategy = cls.dbapi.get_strategy_by_uuid(context, uuid)
        strategy = cls._from_db_object(cls(context), db_strategy)
        return strategy

    @classmethod
    def get_by_name(cls, context, name):
        """Find a strategy based on name

        :param name: the name of a strategy.
        :param context: Security context
        :returns: a :class:`Strategy` object.
        """

        db_strategy = cls.dbapi.get_strategy_by_name(context, name)
        strategy = cls._from_db_object(cls(context), db_strategy)
        return strategy

    @classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None):
        """Return a list of :class:`Strategy` objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        :param filters: dict mapping the filter key to a value.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Strategy` object.
        """
        db_strategies = cls.dbapi.get_strategy_list(
            context,
            filters=filters,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)
        return Strategy._from_db_object_list(db_strategies, cls, context)

    def create(self, context=None):
        """Create a :class:`Strategy` record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Strategy(context)
        """

        values = self.obj_get_changes()
        db_strategy = self.dbapi.create_strategy(values)
        self._from_db_object(self, db_strategy)

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

    def refresh(self, context=None):
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
        """
        current = self.__class__.get_by_id(self._context, strategy_id=self.id)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]

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
