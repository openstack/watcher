# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
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
from oslo_config import cfg

from watcher.notifications import base as notificationbase
from watcher.objects import base
from watcher.objects import fields as wfields
from watcher.objects import service as o_service

CONF = cfg.CONF


@base.WatcherObjectRegistry.register_notification
class ServicePayload(notificationbase.NotificationPayloadBase):

    SCHEMA = {
        'sevice_host': ('failed_service', 'host'),
        'name': ('failed_service', 'name'),
        'last_seen_up': ('failed_service', 'last_seen_up'),
    }
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'sevice_host': wfields.StringField(),
        'name': wfields.StringField(),
        'last_seen_up': wfields.DateTimeField(nullable=True),
    }

    def __init__(self, failed_service, status_update, **kwargs):
        super(ServicePayload, self).__init__(
            failed_service=failed_service,
            status_update=status_update, **kwargs)
        self.populate_schema(failed_service=failed_service)


@base.WatcherObjectRegistry.register_notification
class ServiceStatusUpdatePayload(notificationbase.NotificationPayloadBase):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'old_state': wfields.StringField(nullable=True),
        'state': wfields.StringField(nullable=True),
    }


@base.WatcherObjectRegistry.register_notification
class ServiceUpdatePayload(ServicePayload):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'status_update': wfields.ObjectField('ServiceStatusUpdatePayload'),
    }

    def __init__(self, failed_service, status_update):
        super(ServiceUpdatePayload, self).__init__(
            failed_service=failed_service,
            status_update=status_update)


@notificationbase.notification_sample('service-update.json')
@base.WatcherObjectRegistry.register_notification
class ServiceUpdateNotification(notificationbase.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': wfields.ObjectField('ServiceUpdatePayload')
    }


def send_service_update(context, failed_service, state,
                        service='infra-optim',
                        host=None):
    """Emit an service failed notification."""
    if state == o_service.ServiceStatus.FAILED:
        priority = wfields.NotificationPriority.WARNING
        status_update = ServiceStatusUpdatePayload(
            old_state=o_service.ServiceStatus.ACTIVE,
            state=o_service.ServiceStatus.FAILED)
    else:
        priority = wfields.NotificationPriority.INFO
        status_update = ServiceStatusUpdatePayload(
            old_state=o_service.ServiceStatus.FAILED,
            state=o_service.ServiceStatus.ACTIVE)
    versioned_payload = ServiceUpdatePayload(
        failed_service=failed_service,
        status_update=status_update
    )

    notification = ServiceUpdateNotification(
        priority=priority,
        event_type=notificationbase.EventType(
            object='service',
            action=wfields.NotificationAction.UPDATE),
        publisher=notificationbase.NotificationPublisher(
            host=host or CONF.host,
            binary=service),
        payload=versioned_payload)

    notification.emit(context)
