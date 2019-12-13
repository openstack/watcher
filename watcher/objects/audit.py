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

"""
In the Watcher system, an :ref:`Audit <audit_definition>` is a request for
optimizing a :ref:`Cluster <cluster_definition>`.

The optimization is done in order to satisfy one :ref:`Goal <goal_definition>`
on a given :ref:`Cluster <cluster_definition>`.

For each :ref:`Audit <audit_definition>`, the Watcher system generates an
:ref:`Action Plan <action_plan_definition>`.

An :ref:`Audit <audit_definition>` has a life-cycle and its current state may
be one of the following:

-  **PENDING** : a request for an :ref:`Audit <audit_definition>` has been
   submitted (either manually by the
   :ref:`Administrator <administrator_definition>` or automatically via some
   event handling mechanism) and is in the queue for being processed by the
   :ref:`Watcher Decision Engine <watcher_decision_engine_definition>`
-  **ONGOING** : the :ref:`Audit <audit_definition>` is currently being
   processed by the
   :ref:`Watcher Decision Engine <watcher_decision_engine_definition>`
-  **SUCCEEDED** : the :ref:`Audit <audit_definition>` has been executed
   successfully (note that it may not necessarily produce a
   :ref:`Solution <solution_definition>`).
-  **FAILED** : an error occurred while executing the
   :ref:`Audit <audit_definition>`
-  **DELETED** : the :ref:`Audit <audit_definition>` is still stored in the
   :ref:`Watcher database <watcher_database_definition>` but is not returned
   any more through the Watcher APIs.
-  **CANCELLED** : the :ref:`Audit <audit_definition>` was in **PENDING** or
   **ONGOING** state and was cancelled by the
   :ref:`Administrator <administrator_definition>`
-  **SUSPENDED** : the :ref:`Audit <audit_definition>` was in **ONGOING**
   state and was suspended by the
   :ref:`Administrator <administrator_definition>`
"""

import enum

from watcher.common import exception
from watcher.common import utils
from watcher.db import api as db_api
from watcher import notifications
from watcher import objects
from watcher.objects import base
from watcher.objects import fields as wfields


class State(object):
    ONGOING = 'ONGOING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    DELETED = 'DELETED'
    PENDING = 'PENDING'
    SUSPENDED = 'SUSPENDED'


class AuditType(enum.Enum):
    ONESHOT = 'ONESHOT'
    CONTINUOUS = 'CONTINUOUS'
    EVENT = 'EVENT'


@base.WatcherObjectRegistry.register
class Audit(base.WatcherPersistentObject, base.WatcherObject,
            base.WatcherObjectDictCompat):

    # Version 1.0: Initial version
    # Version 1.1: Added 'goal' and 'strategy' object field
    # Version 1.2: Added 'auto_trigger' boolean field
    # Version 1.3: Added 'next_run_time' DateTime field,
    #              'interval' type has been changed from Integer to String
    # Version 1.4: Added 'name' string field
    # Version 1.5: Added 'hostname' field
    # Version 1.6: Added 'start_time' and 'end_time' DateTime fields
    # Version 1.7: Added 'force' boolean field
    VERSION = '1.7'

    dbapi = db_api.get_instance()

    fields = {
        'id': wfields.IntegerField(),
        'uuid': wfields.UUIDField(),
        'name': wfields.StringField(),
        'audit_type': wfields.StringField(),
        'state': wfields.StringField(),
        'parameters': wfields.FlexibleDictField(nullable=True),
        'interval': wfields.StringField(nullable=True),
        'scope': wfields.FlexibleListOfDictField(nullable=True),
        'goal_id': wfields.IntegerField(),
        'strategy_id': wfields.IntegerField(nullable=True),
        'auto_trigger': wfields.BooleanField(),
        'next_run_time': wfields.DateTimeField(nullable=True,
                                               tzinfo_aware=False),
        'hostname': wfields.StringField(nullable=True),
        'start_time': wfields.DateTimeField(nullable=True, tzinfo_aware=False),
        'end_time': wfields.DateTimeField(nullable=True, tzinfo_aware=False),
        'force': wfields.BooleanField(default=False, nullable=False),

        'goal': wfields.ObjectField('Goal', nullable=True),
        'strategy': wfields.ObjectField('Strategy', nullable=True),
    }

    object_fields = {
        'goal': (objects.Goal, 'goal_id'),
        'strategy': (objects.Strategy, 'strategy_id'),
    }

    def __init__(self, *args, **kwargs):
        if 'force' not in kwargs:
            kwargs['force'] = False
        super(Audit, self).__init__(*args, **kwargs)

    # Proxified field so we can keep the previous value after an update
    _state = None
    _old_state = None

    # NOTE(v-francoise): The way oslo.versionedobjects works is by using a
    # __new__ that will automatically create the attributes referenced in
    # fields. These attributes are properties that raise an exception if no
    # value has been assigned, which means that they store the actual field
    # value in an "_obj_%(field)s" attribute. So because we want to proxify a
    # value that is already proxified, we have to do what you see below.
    @property
    def _obj_state(self):
        return self._state

    @property
    def _obj_old_state(self):
        return self._old_state

    @property
    def old_state(self):
        return self._old_state

    @_obj_old_state.setter
    def _obj_old_state(self, value):
        self._old_state = value

    @_obj_state.setter
    def _obj_state(self, value):
        if self._old_state is None and self._state is None:
            self._state = value
        else:
            self._old_state, self._state = self._state, value

    @base.remotable_classmethod
    def get(cls, context, audit_id, eager=False):
        """Find a audit based on its id or uuid and return a Audit object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param audit_id: the id *or* uuid of a audit.
        :param eager: Load object fields if True (Default: False)
        :returns: a :class:`Audit` object.
        """
        if utils.is_int_like(audit_id):
            return cls.get_by_id(context, audit_id, eager=eager)
        elif utils.is_uuid_like(audit_id):
            return cls.get_by_uuid(context, audit_id, eager=eager)
        else:
            raise exception.InvalidIdentity(identity=audit_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, audit_id, eager=False):
        """Find a audit based on its integer id and return a Audit object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param audit_id: the id of a audit.
        :param eager: Load object fields if True (Default: False)
        :returns: a :class:`Audit` object.
        """
        db_audit = cls.dbapi.get_audit_by_id(context, audit_id, eager=eager)
        audit = cls._from_db_object(cls(context), db_audit, eager=eager)
        return audit

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, eager=False):
        """Find a audit based on uuid and return a :class:`Audit` object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param uuid: the uuid of a audit.
        :param eager: Load object fields if True (Default: False)
        :returns: a :class:`Audit` object.
        """

        db_audit = cls.dbapi.get_audit_by_uuid(context, uuid, eager=eager)
        audit = cls._from_db_object(cls(context), db_audit, eager=eager)
        return audit

    @base.remotable_classmethod
    def get_by_name(cls, context, name, eager=False):
        """Find an audit based on name and return a :class:`Audit` object.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param name: the name of an audit.
        :param eager: Load object fields if True (Default: False)
        :returns: a :class:`Audit` object.
        """

        db_audit = cls.dbapi.get_audit_by_name(context, name, eager=eager)
        audit = cls._from_db_object(cls(context), db_audit, eager=eager)
        return audit

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, filters=None,
             sort_key=None, sort_dir=None, eager=False):
        """Return a list of Audit objects.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Audit(context)
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param filters: Filters to apply. Defaults to None.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param eager: Load object fields if True (Default: False)
        :returns: a list of :class:`Audit` object.

        """
        db_audits = cls.dbapi.get_audit_list(context,
                                             limit=limit,
                                             marker=marker,
                                             filters=filters,
                                             sort_key=sort_key,
                                             sort_dir=sort_dir,
                                             eager=eager)
        return [cls._from_db_object(cls(context), obj, eager=eager)
                for obj in db_audits]

    @base.remotable
    def create(self):
        """Create an :class:`Audit` record in the DB.

        :returns: An :class:`Audit` object.
        """
        values = self.obj_get_changes()
        db_audit = self.dbapi.create_audit(values)
        # Note(v-francoise): Always load eagerly upon creation so we can send
        # notifications containing information about the related relationships
        self._from_db_object(self, db_audit, eager=True)

        def _notify():
            notifications.audit.send_create(self._context, self)

        _notify()

    @base.remotable
    def destroy(self):
        """Delete the Audit from the DB."""
        self.dbapi.destroy_audit(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self):
        """Save updates to this Audit.

        Updates will be made column by column based on the result
        of self.what_changed().
        """
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_audit(self.uuid, updates)
        obj = self._from_db_object(
            self.__class__(self._context), db_obj, eager=False)
        self.obj_refresh(obj)

        def _notify():
            notifications.audit.send_update(
                self._context, self, old_state=self.old_state)

        _notify()

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, eager=False):
        """Loads updates for this Audit.

        Loads a audit with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded audit column by column, if there are any updates.
        :param eager: Load object fields if True (Default: False)
        """
        current = self.get_by_uuid(self._context, uuid=self.uuid, eager=eager)
        self.obj_refresh(current)

    @base.remotable
    def soft_delete(self):
        """Soft Delete the Audit from the DB."""
        self.state = State.DELETED
        self.save()
        db_obj = self.dbapi.soft_delete_audit(self.uuid)
        obj = self._from_db_object(
            self.__class__(self._context), db_obj, eager=False)
        self.obj_refresh(obj)

        def _notify():
            notifications.audit.send_delete(self._context, self)

        _notify()


class AuditStateTransitionManager(object):

    TRANSITIONS = {
        State.PENDING: [State.ONGOING, State.CANCELLED],
        State.ONGOING: [State.FAILED, State.SUCCEEDED,
                        State.CANCELLED, State.SUSPENDED],
        State.FAILED: [State.DELETED],
        State.SUCCEEDED: [State.DELETED],
        State.CANCELLED: [State.DELETED],
        State.SUSPENDED: [State.ONGOING, State.DELETED],
    }

    INACTIVE_STATES = (State.CANCELLED, State.DELETED,
                       State.FAILED, State.SUSPENDED)

    def check_transition(self, initial, new):
        return new in self.TRANSITIONS.get(initial, [])

    def is_inactive(self, audit):
        return audit.state in self.INACTIVE_STATES
