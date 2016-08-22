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
from watcher.objects import base
from watcher.objects import fields as wfields


@base.WatcherObjectRegistry.register
class EfficacyIndicator(base.WatcherPersistentObject, base.WatcherObject,
                        base.WatcherObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': wfields.IntegerField(),
        'uuid': wfields.UUIDField(),
        'action_plan_id': wfields.IntegerField(),
        'name': wfields.StringField(),
        'description': wfields.StringField(nullable=True),
        'unit': wfields.StringField(nullable=True),
        'value': wfields.NumericField(),
    }

    @base.remotable_classmethod
    def get(cls, context, efficacy_indicator_id):
        """Find an efficacy indicator object given its ID or UUID

        :param efficacy_indicator_id: the ID or UUID of an efficacy indicator.
        :returns: a :class:`EfficacyIndicator` object.
        """
        if utils.is_int_like(efficacy_indicator_id):
            return cls.get_by_id(context, efficacy_indicator_id)
        elif utils.is_uuid_like(efficacy_indicator_id):
            return cls.get_by_uuid(context, efficacy_indicator_id)
        else:
            raise exception.InvalidIdentity(identity=efficacy_indicator_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, efficacy_indicator_id):
        """Find an efficacy indicator given its integer ID

        :param efficacy_indicator_id: the id of an efficacy indicator.
        :returns: a :class:`EfficacyIndicator` object.
        """
        db_efficacy_indicator = cls.dbapi.get_efficacy_indicator_by_id(
            context, efficacy_indicator_id)
        efficacy_indicator = EfficacyIndicator._from_db_object(
            cls(context), db_efficacy_indicator)
        return efficacy_indicator

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find an efficacy indicator given its UUID

        :param uuid: the uuid of an efficacy indicator.
        :param context: Security context
        :returns: a :class:`EfficacyIndicator` object.
        """
        db_efficacy_indicator = cls.dbapi.get_efficacy_indicator_by_uuid(
            context, uuid)
        efficacy_indicator = EfficacyIndicator._from_db_object(
            cls(context), db_efficacy_indicator)
        return efficacy_indicator

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None):
        """Return a list of EfficacyIndicator objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param filters: Filters to apply. Defaults to None.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`EfficacyIndicator` object.

        """
        db_efficacy_indicators = cls.dbapi.get_efficacy_indicator_list(
            context,
            limit=limit,
            marker=marker,
            filters=filters,
            sort_key=sort_key,
            sort_dir=sort_dir)

        return [cls._from_db_object(cls(context), obj)
                for obj in db_efficacy_indicators]

    @base.remotable
    def create(self, context=None):
        """Create a EfficacyIndicator record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EfficacyIndicator(context)

        """
        values = self.obj_get_changes()
        db_efficacy_indicator = self.dbapi.create_efficacy_indicator(values)
        self._from_db_object(self, db_efficacy_indicator)

    def destroy(self, context=None):
        """Delete the EfficacyIndicator from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EfficacyIndicator(context)
        """
        self.dbapi.destroy_efficacy_indicator(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this EfficacyIndicator.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EfficacyIndicator(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_efficacy_indicator(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this EfficacyIndicator.

        Loads an efficacy indicator with the same uuid from the database and
        checks for updated attributes. Updates are applied to the loaded
        efficacy indicator column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EfficacyIndicator(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        self.obj_refresh(current)

    @base.remotable
    def soft_delete(self, context=None):
        """Soft Delete the efficacy indicator from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        """
        self.dbapi.soft_delete_efficacy_indicator(self.uuid)
