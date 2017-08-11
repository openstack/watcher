# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

from watcher.common import context as wcontext
from watcher.common import exception
from watcher.notifications import action_plan as ap_notifications
from watcher.notifications import base as notificationbase
from watcher.notifications import exception as exception_notifications
from watcher import objects
from watcher.objects import base
from watcher.objects import fields as wfields

CONF = cfg.CONF


@base.WatcherObjectRegistry.register_notification
class ActionPayload(notificationbase.NotificationPayloadBase):
    SCHEMA = {
        'uuid': ('action', 'uuid'),

        'action_type': ('action', 'action_type'),
        'input_parameters': ('action', 'input_parameters'),
        'state': ('action', 'state'),
        'parents': ('action', 'parents'),

        'created_at': ('action', 'created_at'),
        'updated_at': ('action', 'updated_at'),
        'deleted_at': ('action', 'deleted_at'),
    }

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'uuid': wfields.UUIDField(),
        'action_type': wfields.StringField(nullable=False),
        'input_parameters': wfields.DictField(nullable=False, default={}),
        'state': wfields.StringField(nullable=False),
        'parents': wfields.ListOfUUIDsField(nullable=False, default=[]),
        'action_plan_uuid': wfields.UUIDField(),
        'action_plan': wfields.ObjectField('TerseActionPlanPayload'),

        'created_at': wfields.DateTimeField(nullable=True),
        'updated_at': wfields.DateTimeField(nullable=True),
        'deleted_at': wfields.DateTimeField(nullable=True),
    }

    def __init__(self, action, **kwargs):
        super(ActionPayload, self).__init__(**kwargs)
        self.populate_schema(action=action)


@base.WatcherObjectRegistry.register_notification
class ActionStateUpdatePayload(notificationbase.NotificationPayloadBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'old_state': wfields.StringField(nullable=True),
        'state': wfields.StringField(nullable=True),
    }


@base.WatcherObjectRegistry.register_notification
class ActionCreatePayload(ActionPayload):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {}

    def __init__(self, action, action_plan):
        super(ActionCreatePayload, self).__init__(
            action=action,
            action_plan=action_plan)


@base.WatcherObjectRegistry.register_notification
class ActionUpdatePayload(ActionPayload):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'state_update': wfields.ObjectField('ActionStateUpdatePayload'),
    }

    def __init__(self, action, state_update, action_plan):
        super(ActionUpdatePayload, self).__init__(
            action=action,
            state_update=state_update,
            action_plan=action_plan)


@base.WatcherObjectRegistry.register_notification
class ActionExecutionPayload(ActionPayload):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'fault': wfields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, action, action_plan, **kwargs):
        super(ActionExecutionPayload, self).__init__(
            action=action,
            action_plan=action_plan,
            **kwargs)


@base.WatcherObjectRegistry.register_notification
class ActionCancelPayload(ActionPayload):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'fault': wfields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, action, action_plan, **kwargs):
        super(ActionCancelPayload, self).__init__(
            action=action,
            action_plan=action_plan,
            **kwargs)


@base.WatcherObjectRegistry.register_notification
class ActionDeletePayload(ActionPayload):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {}

    def __init__(self, action, action_plan):
        super(ActionDeletePayload, self).__init__(
            action=action,
            action_plan=action_plan)


@notificationbase.notification_sample('action-execution-error.json')
@notificationbase.notification_sample('action-execution-end.json')
@notificationbase.notification_sample('action-execution-start.json')
@base.WatcherObjectRegistry.register_notification
class ActionExecutionNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionExecutionPayload')
    }


@notificationbase.notification_sample('action-create.json')
@base.WatcherObjectRegistry.register_notification
class ActionCreateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionCreatePayload')
    }


@notificationbase.notification_sample('action-update.json')
@base.WatcherObjectRegistry.register_notification
class ActionUpdateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionUpdatePayload')
    }


@notificationbase.notification_sample('action-delete.json')
@base.WatcherObjectRegistry.register_notification
class ActionDeleteNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionDeletePayload')
    }


@notificationbase.notification_sample('action-cancel-error.json')
@notificationbase.notification_sample('action-cancel-end.json')
@notificationbase.notification_sample('action-cancel-start.json')
@base.WatcherObjectRegistry.register_notification
class ActionCancelNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionCancelPayload')
    }


def _get_action_plan_payload(action):
    action_plan = None
    strategy_uuid = None
    audit = None
    try:
        action_plan = action.action_plan
        audit = objects.Audit.get(wcontext.make_context(show_deleted=True),
                                  action_plan.audit_id)
        if audit.strategy_id:
            strategy_uuid = objects.Strategy.get(
                wcontext.make_context(show_deleted=True),
                audit.strategy_id).uuid
    except NotImplementedError:
        raise exception.EagerlyLoadedActionRequired(action=action.uuid)

    action_plan_payload = ap_notifications.TerseActionPlanPayload(
        action_plan=action_plan,
        audit_uuid=audit.uuid, strategy_uuid=strategy_uuid)

    return action_plan_payload


def send_create(context, action, service='infra-optim', host=None):
    """Emit an action.create notification."""
    action_plan_payload = _get_action_plan_payload(action)

    versioned_payload = ActionCreatePayload(
        action=action,
        action_plan=action_plan_payload,
    )

    notification = ActionCreateNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='action',
            action=wfields.NotificationAction.CREATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_update(context, action, service='infra-optim',
                host=None, old_state=None):
    """Emit an action.update notification."""
    action_plan_payload = _get_action_plan_payload(action)

    state_update = ActionStateUpdatePayload(
        old_state=old_state,
        state=action.state if old_state else None)

    versioned_payload = ActionUpdatePayload(
        action=action,
        state_update=state_update,
        action_plan=action_plan_payload,
    )

    notification = ActionUpdateNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='action',
            action=wfields.NotificationAction.UPDATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_delete(context, action, service='infra-optim', host=None):
    """Emit an action.delete notification."""
    action_plan_payload = _get_action_plan_payload(action)

    versioned_payload = ActionDeletePayload(
        action=action,
        action_plan=action_plan_payload,
    )

    notification = ActionDeleteNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='action',
            action=wfields.NotificationAction.DELETE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_execution_notification(context, action, notification_action, phase,
                                priority=wfields.NotificationPriority.INFO,
                                service='infra-optim', host=None):
    """Emit an action execution notification."""
    action_plan_payload = _get_action_plan_payload(action)

    fault = None
    if phase == wfields.NotificationPhase.ERROR:
        fault = exception_notifications.ExceptionPayload.from_exception()

    versioned_payload = ActionExecutionPayload(
        action=action,
        action_plan=action_plan_payload,
        fault=fault,
    )

    notification = ActionExecutionNotification(
        priority=priority,
        event_type=notificationbase.EventType(
            object='action',
            action=notification_action,
            phase=phase),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_cancel_notification(context, action, notification_action, phase,
                             priority=wfields.NotificationPriority.INFO,
                             service='infra-optim', host=None):
    """Emit an action cancel notification."""
    action_plan_payload = _get_action_plan_payload(action)

    fault = None
    if phase == wfields.NotificationPhase.ERROR:
        fault = exception_notifications.ExceptionPayload.from_exception()

    versioned_payload = ActionCancelPayload(
        action=action,
        action_plan=action_plan_payload,
        fault=fault,
    )

    notification = ActionCancelNotification(
        priority=priority,
        event_type=notificationbase.EventType(
            object='action',
            action=notification_action,
            phase=phase),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)
