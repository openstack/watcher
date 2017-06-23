# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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

from watcher.common import exception
from watcher.notifications import base as notificationbase
from watcher.notifications import exception as exception_notifications
from watcher.notifications import goal as goal_notifications
from watcher.notifications import strategy as strategy_notifications
from watcher.objects import base
from watcher.objects import fields as wfields

CONF = cfg.CONF


@base.WatcherObjectRegistry.register_notification
class TerseAuditPayload(notificationbase.NotificationPayloadBase):
    SCHEMA = {
        'uuid': ('audit', 'uuid'),
        'name': ('audit', 'name'),
        'audit_type': ('audit', 'audit_type'),
        'state': ('audit', 'state'),
        'parameters': ('audit', 'parameters'),
        'interval': ('audit', 'interval'),
        'scope': ('audit', 'scope'),
        'auto_trigger': ('audit', 'auto_trigger'),
        'next_run_time': ('audit', 'next_run_time'),

        'created_at': ('audit', 'created_at'),
        'updated_at': ('audit', 'updated_at'),
        'deleted_at': ('audit', 'deleted_at'),
    }

    # Version 1.0: Initial version
    # Version 1.1: Added 'auto_trigger' boolean field,
    #              Added 'next_run_time' DateTime field,
    #              'interval' type has been changed from Integer to String
    # Version 1.2: Added 'name' string field
    VERSION = '1.2'

    fields = {
        'uuid': wfields.UUIDField(),
        'name': wfields.StringField(),
        'audit_type': wfields.StringField(),
        'state': wfields.StringField(),
        'parameters': wfields.FlexibleDictField(nullable=True),
        'interval': wfields.StringField(nullable=True),
        'scope': wfields.FlexibleListOfDictField(nullable=True),
        'goal_uuid': wfields.UUIDField(),
        'strategy_uuid': wfields.UUIDField(nullable=True),
        'auto_trigger': wfields.BooleanField(),
        'next_run_time': wfields.DateTimeField(nullable=True),

        'created_at': wfields.DateTimeField(nullable=True),
        'updated_at': wfields.DateTimeField(nullable=True),
        'deleted_at': wfields.DateTimeField(nullable=True),
    }

    def __init__(self, audit, goal_uuid, strategy_uuid=None, **kwargs):
        super(TerseAuditPayload, self).__init__(
            goal_uuid=goal_uuid, strategy_uuid=strategy_uuid, **kwargs)
        self.populate_schema(audit=audit)


@base.WatcherObjectRegistry.register_notification
class AuditPayload(TerseAuditPayload):
    SCHEMA = {
        'uuid': ('audit', 'uuid'),
        'name': ('audit', 'name'),
        'audit_type': ('audit', 'audit_type'),
        'state': ('audit', 'state'),
        'parameters': ('audit', 'parameters'),
        'interval': ('audit', 'interval'),
        'scope': ('audit', 'scope'),
        'auto_trigger': ('audit', 'auto_trigger'),
        'next_run_time': ('audit', 'next_run_time'),

        'created_at': ('audit', 'created_at'),
        'updated_at': ('audit', 'updated_at'),
        'deleted_at': ('audit', 'deleted_at'),
    }

    # Version 1.0: Initial version
    # Version 1.1: Added 'auto_trigger' field,
    #              Added 'next_run_time' field
    # Version 1.2: Added 'name' string field
    VERSION = '1.2'

    fields = {
        'goal': wfields.ObjectField('GoalPayload'),
        'strategy': wfields.ObjectField('StrategyPayload', nullable=True),
    }

    def __init__(self, audit, goal, strategy=None, **kwargs):
        if not kwargs.get('goal_uuid'):
            kwargs['goal_uuid'] = goal.uuid

        if strategy and not kwargs.get('strategy_uuid'):
            kwargs['strategy_uuid'] = strategy.uuid

        super(AuditPayload, self).__init__(
            audit=audit, goal=goal,
            strategy=strategy, **kwargs)


@base.WatcherObjectRegistry.register_notification
class AuditStateUpdatePayload(notificationbase.NotificationPayloadBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'old_state': wfields.StringField(nullable=True),
        'state': wfields.StringField(nullable=True),
    }


@base.WatcherObjectRegistry.register_notification
class AuditCreatePayload(AuditPayload):
    # Version 1.0: Initial version
    # Version 1.1: Added 'auto_trigger' field,
    #              Added 'next_run_time' field
    VERSION = '1.1'
    fields = {}

    def __init__(self, audit, goal, strategy):
        super(AuditCreatePayload, self).__init__(
            audit=audit,
            goal=goal,
            goal_uuid=goal.uuid,
            strategy=strategy)


@base.WatcherObjectRegistry.register_notification
class AuditUpdatePayload(AuditPayload):
    # Version 1.0: Initial version
    # Version 1.1: Added 'auto_trigger' field,
    #              Added 'next_run_time' field
    VERSION = '1.1'
    fields = {
        'state_update': wfields.ObjectField('AuditStateUpdatePayload'),
    }

    def __init__(self, audit, state_update, goal, strategy):
        super(AuditUpdatePayload, self).__init__(
            audit=audit,
            state_update=state_update,
            goal=goal,
            goal_uuid=goal.uuid,
            strategy=strategy)


@base.WatcherObjectRegistry.register_notification
class AuditActionPayload(AuditPayload):
    # Version 1.0: Initial version
    # Version 1.1: Added 'auto_trigger' field,
    #              Added 'next_run_time' field
    VERSION = '1.1'
    fields = {
        'fault': wfields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, audit, goal, strategy, **kwargs):
        super(AuditActionPayload, self).__init__(
            audit=audit,
            goal=goal,
            goal_uuid=goal.uuid,
            strategy=strategy,
            **kwargs)


@base.WatcherObjectRegistry.register_notification
class AuditDeletePayload(AuditPayload):
    # Version 1.0: Initial version
    # Version 1.1: Added 'auto_trigger' field,
    #              Added 'next_run_time' field
    VERSION = '1.1'
    fields = {}

    def __init__(self, audit, goal, strategy):
        super(AuditDeletePayload, self).__init__(
            audit=audit,
            goal=goal,
            goal_uuid=goal.uuid,
            strategy=strategy)


@notificationbase.notification_sample('audit-strategy-error.json')
@notificationbase.notification_sample('audit-strategy-end.json')
@notificationbase.notification_sample('audit-strategy-start.json')
@base.WatcherObjectRegistry.register_notification
class AuditActionNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('AuditActionPayload')
    }


@notificationbase.notification_sample('audit-create.json')
@base.WatcherObjectRegistry.register_notification
class AuditCreateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('AuditCreatePayload')
    }


@notificationbase.notification_sample('audit-update.json')
@base.WatcherObjectRegistry.register_notification
class AuditUpdateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('AuditUpdatePayload')
    }


@notificationbase.notification_sample('audit-delete.json')
@base.WatcherObjectRegistry.register_notification
class AuditDeleteNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('AuditDeletePayload')
    }


def _get_common_payload(audit):
    goal = None
    strategy = None
    try:
        goal = audit.goal
        if audit.strategy_id:
            strategy = audit.strategy
    except NotImplementedError:
        raise exception.EagerlyLoadedAuditRequired(audit=audit.uuid)

    goal_payload = goal_notifications.GoalPayload(goal=goal)

    strategy_payload = None
    if strategy:
        strategy_payload = strategy_notifications.StrategyPayload(
            strategy=strategy)

    return goal_payload, strategy_payload


def send_create(context, audit, service='infra-optim', host=None):
    """Emit an audit.create notification."""
    goal_payload, strategy_payload = _get_common_payload(audit)

    versioned_payload = AuditCreatePayload(
        audit=audit,
        goal=goal_payload,
        strategy=strategy_payload,
    )

    notification = AuditCreateNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='audit',
            action=wfields.NotificationAction.CREATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_update(context, audit, service='infra-optim',
                host=None, old_state=None):
    """Emit an audit.update notification."""
    goal_payload, strategy_payload = _get_common_payload(audit)

    state_update = AuditStateUpdatePayload(
        old_state=old_state,
        state=audit.state if old_state else None)

    versioned_payload = AuditUpdatePayload(
        audit=audit,
        state_update=state_update,
        goal=goal_payload,
        strategy=strategy_payload,
    )

    notification = AuditUpdateNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='audit',
            action=wfields.NotificationAction.UPDATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_delete(context, audit, service='infra-optim', host=None):
    goal_payload, strategy_payload = _get_common_payload(audit)

    versioned_payload = AuditDeletePayload(
        audit=audit,
        goal=goal_payload,
        strategy=strategy_payload,
    )

    notification = AuditDeleteNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='audit',
            action=wfields.NotificationAction.DELETE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_action_notification(context, audit, action, phase=None,
                             priority=wfields.NotificationPriority.INFO,
                             service='infra-optim', host=None):
    """Emit an audit action notification."""
    goal_payload, strategy_payload = _get_common_payload(audit)

    fault = None
    if phase == wfields.NotificationPhase.ERROR:
        fault = exception_notifications.ExceptionPayload.from_exception()

    versioned_payload = AuditActionPayload(
        audit=audit,
        goal=goal_payload,
        strategy=strategy_payload,
        fault=fault,
    )

    notification = AuditActionNotification(
        priority=priority,
        event_type=notificationbase.EventType(
            object='audit',
            action=action,
            phase=phase),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)
