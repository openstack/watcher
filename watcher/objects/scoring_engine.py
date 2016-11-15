# -*- encoding: utf-8 -*-
# Copyright 2016 Intel
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

"""
A :ref:`Scoring Engine <scoring_engine_definition>` is an instance of a data
model, to which a learning data was applied.

Because there might be multiple algorithms used to build a particular data
model (and therefore a scoring engine), the usage of scoring engine might
vary. A metainfo field is supposed to contain any information which might
be needed by the user of a given scoring engine.
"""

from watcher.common import exception
from watcher.common import utils
from watcher.db import api as db_api
from watcher.objects import base
from watcher.objects import fields as wfields


@base.WatcherObjectRegistry.register
class ScoringEngine(base.WatcherPersistentObject, base.WatcherObject,
                    base.WatcherObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': wfields.IntegerField(),
        'uuid': wfields.UUIDField(),
        'name': wfields.StringField(),
        'description': wfields.StringField(nullable=True),
        'metainfo': wfields.StringField(nullable=True),
    }

    @base.remotable_classmethod
    def get(cls, context, scoring_engine_id):
        """Find a scoring engine based on its id or uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        :param scoring_engine_name: the name of a scoring_engine.
        :returns: a :class:`ScoringEngine` object.
        """
        if utils.is_int_like(scoring_engine_id):
            return cls.get_by_id(context, scoring_engine_id)
        elif utils.is_uuid_like(scoring_engine_id):
            return cls.get_by_uuid(context, scoring_engine_id)
        else:
            raise exception.InvalidIdentity(identity=scoring_engine_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, scoring_engine_id):
        """Find a scoring engine based on its id

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        :param scoring_engine_id: the id of a scoring_engine.
        :returns: a :class:`ScoringEngine` object.
        """
        db_scoring_engine = cls.dbapi.get_scoring_engine_by_id(
            context,
            scoring_engine_id)
        scoring_engine = ScoringEngine._from_db_object(cls(context),
                                                       db_scoring_engine)
        return scoring_engine

    @base.remotable_classmethod
    def get_by_uuid(cls, context, scoring_engine_uuid):
        """Find a scoring engine based on its uuid

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        :param scoring_engine_uuid: the uuid of a scoring_engine.
        :returns: a :class:`ScoringEngine` object.
        """
        db_scoring_engine = cls.dbapi.get_scoring_engine_by_uuid(
            context,
            scoring_engine_uuid)
        scoring_engine = ScoringEngine._from_db_object(cls(context),
                                                       db_scoring_engine)
        return scoring_engine

    @base.remotable_classmethod
    def get_by_name(cls, context, scoring_engine_name):
        """Find a scoring engine based on its name

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        :param scoring_engine_name: the name of a scoring_engine.
        :returns: a :class:`ScoringEngine` object.
        """
        db_scoring_engine = cls.dbapi.get_scoring_engine_by_name(
            context,
            scoring_engine_name)
        scoring_engine = ScoringEngine._from_db_object(cls(context),
                                                       db_scoring_engine)
        return scoring_engine

    @base.remotable_classmethod
    def list(cls, context, filters=None, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of :class:`ScoringEngine` objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        :param filters: dict mapping the filter key to a value.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`ScoringEngine` objects.
        """
        db_scoring_engines = cls.dbapi.get_scoring_engine_list(
            context,
            filters=filters,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)
        return [cls._from_db_object(cls(context), obj)
                for obj in db_scoring_engines]

    @base.remotable
    def create(self):
        """Create a :class:`ScoringEngine` record in the DB."""
        values = self.obj_get_changes()
        db_scoring_engine = self.dbapi.create_scoring_engine(values)
        self._from_db_object(self, db_scoring_engine)

    def destroy(self):
        """Delete the :class:`ScoringEngine` from the DB"""
        self.dbapi.destroy_scoring_engine(self.id)
        self.obj_reset_changes()

    @base.remotable
    def save(self):
        """Save updates to this :class:`ScoringEngine`.

        Updates will be made column by column based on the result
        of self.what_changed().
        """
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_scoring_engine(self.uuid, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    def refresh(self):
        """Loads updates for this :class:`ScoringEngine`.

        Loads a scoring_engine with the same id from the database and
        checks for updated attributes. Updates are applied from
        the loaded scoring_engine column by column, if there are any updates.
        """
        current = self.get_by_id(self._context, scoring_engine_id=self.id)
        self.obj_refresh(current)

    def soft_delete(self):
        """Soft Delete the :class:`ScoringEngine` from the DB"""
        db_obj = self.dbapi.soft_delete_scoring_engine(self.id)
        obj = self._from_db_object(
            self.__class__(self._context), db_obj, eager=False)
        self.obj_refresh(obj)
