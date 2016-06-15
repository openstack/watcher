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
from watcher.db import api as dbapi
from watcher.objects import base
from watcher.objects import utils as obj_utils


class ScoringEngine(base.WatcherObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'description': obj_utils.str_or_none,
        'metainfo': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(scoring_engine, db_scoring_engine):
        """Converts a database entity to a formal object."""
        for field in scoring_engine.fields:
            scoring_engine[field] = db_scoring_engine[field]

        scoring_engine.obj_reset_changes()
        return scoring_engine

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return \
            [ScoringEngine._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
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

    @classmethod
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

    @classmethod
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

    @classmethod
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

    @classmethod
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
        return ScoringEngine._from_db_object_list(db_scoring_engines,
                                                  cls, context)

    def create(self, context=None):
        """Create a :class:`ScoringEngine` record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        """

        values = self.obj_get_changes()
        db_scoring_engine = self.dbapi.create_scoring_engine(values)
        self._from_db_object(self, db_scoring_engine)

    def destroy(self, context=None):
        """Delete the :class:`ScoringEngine` from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        """

        self.dbapi.destroy_scoring_engine(self.id)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this :class:`ScoringEngine`.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        """

        updates = self.obj_get_changes()
        self.dbapi.update_scoring_engine(self.id, updates)

        self.obj_reset_changes()

    def refresh(self, context=None):
        """Loads updates for this :class:`ScoringEngine`.

        Loads a scoring_engine with the same id from the database and
        checks for updated attributes. Updates are applied from
        the loaded scoring_engine column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        """

        current = self.__class__.get_by_id(self._context,
                                           scoring_engine_id=self.id)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]

    def soft_delete(self, context=None):
        """soft Delete the :class:`ScoringEngine` from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ScoringEngine(context)
        """

        self.dbapi.soft_delete_scoring_engine(self.id)
