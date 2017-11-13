# -*- encoding: utf-8 -*-
# Copyright (c) 2017 b<>com
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

from watcher.common import context as wcontext
from watcher.common import exception
from watcher.notifications import audit as audit_notifications
from watcher.notifications import base as notificationbase
from watcher.notifications import exception as exception_notifications
from watcher.notifications import strategy as strategy_notifications
from watcher import objects
from watcher.objects import base
from watcher.objects import fields as wfields

CONF = cfg.CONF


@base.WatcherObjectRegistry.register_notification
class TerseActionPlanPayload(notificationbase.NotificationPayloadBase):
    SCHEMA = {
        'uuid': ('action_plan', 'uuid'),

        'state': ('action_plan', 'state'),
        'global_efficacy': ('action_plan', 'global_efficacy'),

        'created_at': ('action_plan', 'created_at'),
        'updated_at': ('action_plan', 'updated_at'),
        'deleted_at': ('action_plan', 'deleted_at'),
    }

    # Version 1.0: Initial version
    # Version 1.1: Changed 'global_efficacy' type Dictionary to List
    VERSION = '1.1'

    fields = {
        'uuid': wfields.UUIDField(),
        'state': wfields.StringField(),
        'global_efficacy': wfields.FlexibleListOfDictField(nullable=True),
        'audit_uuid': wfields.UUIDField(),
        'strategy_uuid': wfields.UUIDField(nullable=True),

        'created_at': wfields.DateTimeField(nullable=True),
        'updated_at': wfields.DateTimeField(nullable=True),
        'deleted_at': wfields.DateTimeField(nullable=True),
    }

    def __init__(self, action_plan, audit=None, strategy=None, **kwargs):
        super(TerseActionPlanPayload, self).__init__(audit=audit,
                                                     strategy=strategy,
                                                     **kwargs)
        self.populate_schema(action_plan=action_plan)


@base.WatcherObjectRegistry.register_notification
class ActionPlanPayload(TerseActionPlanPayload):
    SCHEMA = {
        'uuid': ('action_plan', 'uuid'),

        'state': ('action_plan', 'state'),
        'global_efficacy': ('action_plan', 'global_efficacy'),

        'created_at': ('action_plan', 'created_at'),
        'updated_at': ('action_plan', 'updated_at'),
        'deleted_at': ('action_plan', 'deleted_at'),
    }

    # Version 1.0: Initial version
    # Vesrsion 1.1: changed global_efficacy type
    VERSION = '1.1'

    fields = {
        'audit': wfields.ObjectField('TerseAuditPayload'),
        'strategy': wfields.ObjectField('StrategyPayload'),
    }

    def __init__(self, action_plan, audit, strategy, **kwargs):
        if not kwargs.get('audit_uuid'):
            kwargs['audit_uuid'] = audit.uuid

        if strategy and not kwargs.get('strategy_uuid'):
            kwargs['strategy_uuid'] = strategy.uuid

        super(ActionPlanPayload, self).__init__(
            action_plan, audit=audit, strategy=strategy, **kwargs)


@base.WatcherObjectRegistry.register_notification
class ActionPlanStateUpdatePayload(notificationbase.NotificationPayloadBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'old_state': wfields.StringField(nullable=True),
        'state': wfields.StringField(nullable=True),
    }


@base.WatcherObjectRegistry.register_notification
class ActionPlanCreatePayload(ActionPlanPayload):
    # Version 1.0: Initial version
    # Version 1.1: Changed global_efficacy_type
    VERSION = '1.1'
    fields = {}

    def __init__(self, action_plan, audit, strategy):
        super(ActionPlanCreatePayload, self).__init__(
            action_plan=action_plan,
            audit=audit,
            strategy=strategy)


@base.WatcherObjectRegistry.register_notification
class ActionPlanUpdatePayload(ActionPlanPayload):
    # Version 1.0: Initial version
    # Version 1.1: Changed global_efficacy_type
    VERSION = '1.1'
    fields = {
        'state_update': wfields.ObjectField('ActionPlanStateUpdatePayload'),
    }

    def __init__(self, action_plan, state_update, audit, strategy):
        super(ActionPlanUpdatePayload, self).__init__(
            action_plan=action_plan,
            state_update=state_update,
            audit=audit,
            strategy=strategy)


@base.WatcherObjectRegistry.register_notification
class ActionPlanActionPayload(ActionPlanPayload):
    # Version 1.0: Initial version
    # Version 1.1: Changed global_efficacy_type
    VERSION = '1.1'
    fields = {
        'fault': wfields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, action_plan, audit, strategy, **kwargs):
        super(ActionPlanActionPayload, self).__init__(
            action_plan=action_plan,
            audit=audit,
            strategy=strategy,
            **kwargs)


@base.WatcherObjectRegistry.register_notification
class ActionPlanDeletePayload(ActionPlanPayload):
    # Version 1.0: Initial version
    # Version 1.1: Changed global_efficacy_type
    VERSION = '1.1'
    fields = {}

    def __init__(self, action_plan, audit, strategy):
        super(ActionPlanDeletePayload, self).__init__(
            action_plan=action_plan,
            audit=audit,
            strategy=strategy)


@base.WatcherObjectRegistry.register_notification
class ActionPlanCancelPayload(ActionPlanPayload):
    # Version 1.0: Initial version
    # Version 1.1: Changed global_efficacy_type
    VERSION = '1.1'
    fields = {
        'fault': wfields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, action_plan, audit, strategy, **kwargs):
        super(ActionPlanCancelPayload, self).__init__(
            action_plan=action_plan,
            audit=audit,
            strategy=strategy,
            **kwargs)


@notificationbase.notification_sample('action_plan-execution-error.json')
@notificationbase.notification_sample('action_plan-execution-end.json')
@notificationbase.notification_sample('action_plan-execution-start.json')
@base.WatcherObjectRegistry.register_notification
class ActionPlanActionNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionPlanActionPayload')
    }


@notificationbase.notification_sample('action_plan-create.json')
@base.WatcherObjectRegistry.register_notification
class ActionPlanCreateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionPlanCreatePayload')
    }


@notificationbase.notification_sample('action_plan-update.json')
@base.WatcherObjectRegistry.register_notification
class ActionPlanUpdateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionPlanUpdatePayload')
    }


@notificationbase.notification_sample('action_plan-delete.json')
@base.WatcherObjectRegistry.register_notification
class ActionPlanDeleteNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionPlanDeletePayload')
    }


@notificationbase.notification_sample('action_plan-cancel-error.json')
@notificationbase.notification_sample('action_plan-cancel-end.json')
@notificationbase.notification_sample('action_plan-cancel-start.json')
@base.WatcherObjectRegistry.register_notification
class ActionPlanCancelNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ActionPlanCancelPayload')
    }


def _get_common_payload(action_plan):
    audit = None
    strategy = None
    try:
        audit = action_plan.audit
        strategy = action_plan.strategy
    except NotImplementedError:
        raise exception.EagerlyLoadedActionPlanRequired(
            action_plan=action_plan.uuid)

    goal = objects.Goal.get(
        wcontext.make_context(show_deleted=True), audit.goal_id)
    audit_payload = audit_notifications.TerseAuditPayload(
        audit=audit, goal_uuid=goal.uuid)

    strategy_payload = strategy_notifications.StrategyPayload(
        strategy=strategy)

    return audit_payload, strategy_payload


def send_create(context, action_plan, service='infra-optim', host=None):
    """Emit an action_plan.create notification."""
    audit_payload, strategy_payload = _get_common_payload(action_plan)

    versioned_payload = ActionPlanCreatePayload(
        action_plan=action_plan,
        audit=audit_payload,
        strategy=strategy_payload,
    )

    notification = ActionPlanCreateNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='action_plan',
            action=wfields.NotificationAction.CREATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_update(context, action_plan, service='infra-optim',
                host=None, old_state=None):
    """Emit an action_plan.update notification."""
    audit_payload, strategy_payload = _get_common_payload(action_plan)

    state_update = ActionPlanStateUpdatePayload(
        old_state=old_state,
        state=action_plan.state if old_state else None)

    versioned_payload = ActionPlanUpdatePayload(
        action_plan=action_plan,
        state_update=state_update,
        audit=audit_payload,
        strategy=strategy_payload,
    )

    notification = ActionPlanUpdateNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='action_plan',
            action=wfields.NotificationAction.UPDATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_delete(context, action_plan, service='infra-optim', host=None):
    """Emit an action_plan.delete notification."""
    audit_payload, strategy_payload = _get_common_payload(action_plan)

    versioned_payload = ActionPlanDeletePayload(
        action_plan=action_plan,
        audit=audit_payload,
        strategy=strategy_payload,
    )

    notification = ActionPlanDeleteNotification(
        priority=wfields.NotificationPriority.INFO,
        event_type=notificationbase.EventType(
            object='action_plan',
            action=wfields.NotificationAction.DELETE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_action_notification(context, action_plan, action, phase=None,
                             priority=wfields.NotificationPriority.INFO,
                             service='infra-optim', host=None):
    """Emit an action_plan action notification."""
    audit_payload, strategy_payload = _get_common_payload(action_plan)

    fault = None
    if phase == wfields.NotificationPhase.ERROR:
        fault = exception_notifications.ExceptionPayload.from_exception()

    versioned_payload = ActionPlanActionPayload(
        action_plan=action_plan,
        audit=audit_payload,
        strategy=strategy_payload,
        fault=fault,
    )

    notification = ActionPlanActionNotification(
        priority=priority,
        event_type=notificationbase.EventType(
            object='action_plan',
            action=action,
            phase=phase),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)


def send_cancel_notification(context, action_plan, action, phase=None,
                             priority=wfields.NotificationPriority.INFO,
                             service='infra-optim', host=None):
    """Emit an action_plan cancel notification."""
    audit_payload, strategy_payload = _get_common_payload(action_plan)

    fault = None
    if phase == wfields.NotificationPhase.ERROR:
        fault = exception_notifications.ExceptionPayload.from_exception()

    versioned_payload = ActionPlanCancelPayload(
        action_plan=action_plan,
        audit=audit_payload,
        strategy=strategy_payload,
        fault=fault,
    )

    notification = ActionPlanCancelNotification(
        priority=priority,
        event_type=notificationbase.EventType(
            object='action_plan',
            action=action,
            phase=phase),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)
