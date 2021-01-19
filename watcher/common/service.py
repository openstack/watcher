# -*- encoding: utf-8 -*-
#
# Copyright © 2012 eNovance <licensing@enovance.com>
##
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime
import socket

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import _options
from oslo_log import log
import oslo_messaging as messaging
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts
from oslo_service import service
from oslo_service import wsgi

from watcher._i18n import _
from watcher.api import app
from watcher.common import config
from watcher.common import context
from watcher.common import rpc
from watcher.common import scheduling
from watcher.conf import plugins as plugins_conf
from watcher import objects
from watcher.objects import base
from watcher.objects import fields as wfields
from watcher import version


NOTIFICATION_OPTS = [
    cfg.StrOpt('notification_level',
               choices=[''] + list(wfields.NotificationPriority.ALL),
               default=wfields.NotificationPriority.INFO,
               help=_('Specifies the minimum level for which to send '
                      'notifications. If not set, no notifications will '
                      'be sent. The default is for this option to be at the '
                      '`INFO` level.'))
]
cfg.CONF.register_opts(NOTIFICATION_OPTS)


CONF = cfg.CONF
LOG = log.getLogger(__name__)

_DEFAULT_LOG_LEVELS = ['amqp=WARN', 'amqplib=WARN', 'qpid.messaging=INFO',
                       'oslo.messaging=INFO', 'sqlalchemy=WARN',
                       'keystoneclient=INFO', 'stevedore=INFO',
                       'eventlet.wsgi.server=WARN', 'iso8601=WARN',
                       'requests=WARN', 'neutronclient=WARN',
                       'glanceclient=WARN',
                       'apscheduler=WARN']

Singleton = service.Singleton


class WSGIService(service.ServiceBase):
    """Provides ability to launch Watcher API from wsgi app."""

    def __init__(self, service_name, use_ssl=False):
        """Initialize, but do not start the WSGI server.

        :param service_name: The service name of the WSGI server.
        :param use_ssl: Wraps the socket in an SSL context if True.
        """
        self.service_name = service_name
        self.app = app.VersionSelectorApplication()
        self.workers = (CONF.api.workers or
                        processutils.get_worker_count())
        self.server = wsgi.Server(CONF, self.service_name, self.app,
                                  host=CONF.api.host,
                                  port=CONF.api.port,
                                  use_ssl=use_ssl,
                                  logger_name=self.service_name)

    def start(self):
        """Start serving this service using loaded configuration"""
        self.server.start()

    def stop(self):
        """Stop serving this API"""
        self.server.stop()

    def wait(self):
        """Wait for the service to stop serving this API"""
        self.server.wait()

    def reset(self):
        """Reset server greenpool size to default"""
        self.server.reset()


class ServiceHeartbeat(scheduling.BackgroundSchedulerService):

    service_name = None

    def __init__(self, gconfig=None, service_name=None, **kwargs):
        gconfig = None or {}
        super(ServiceHeartbeat, self).__init__(gconfig, **kwargs)
        ServiceHeartbeat.service_name = service_name
        self.context = context.make_context()
        self.send_beat()

    def send_beat(self):
        host = CONF.host
        watcher_list = objects.Service.list(
            self.context, filters={'name': ServiceHeartbeat.service_name,
                                   'host': host})
        if watcher_list:
            watcher_service = watcher_list[0]
            watcher_service.last_seen_up = datetime.datetime.utcnow()
            watcher_service.save()
        else:
            watcher_service = objects.Service(self.context)
            watcher_service.name = ServiceHeartbeat.service_name
            watcher_service.host = host
            watcher_service.create()

    def add_heartbeat_job(self):
        self.add_job(self.send_beat, 'interval', seconds=60,
                     next_run_time=datetime.datetime.now())

    @classmethod
    def get_service_name(cls):
        return CONF.host, cls.service_name

    def start(self):
        """Start service."""
        self.add_heartbeat_job()
        super(ServiceHeartbeat, self).start()

    def stop(self):
        """Stop service."""
        self.shutdown()

    def wait(self):
        """Wait for service to complete."""

    def reset(self):
        """Reset service.

        Called in case service running in daemon mode receives SIGHUP.
        """


class Service(service.ServiceBase):

    API_VERSION = '1.0'

    def __init__(self, manager_class):
        super(Service, self).__init__()
        self.manager = manager_class()

        self.publisher_id = self.manager.publisher_id
        self.api_version = self.manager.api_version

        self.conductor_topic = self.manager.conductor_topic
        self.notification_topics = self.manager.notification_topics

        self.heartbeat = None

        self.service_name = self.manager.service_name
        if self.service_name:
            self.heartbeat = ServiceHeartbeat(
                service_name=self.manager.service_name)

        self.conductor_endpoints = [
            ep(self) for ep in self.manager.conductor_endpoints
        ]
        self.notification_endpoints = self.manager.notification_endpoints

        self._conductor_client = None

        self.conductor_topic_handler = None
        self.notification_handler = None

        if self.conductor_topic and self.conductor_endpoints:
            self.conductor_topic_handler = self.build_topic_handler(
                self.conductor_topic, self.conductor_endpoints)
        if self.notification_topics and self.notification_endpoints:
            self.notification_handler = self.build_notification_handler(
                self.notification_topics, self.notification_endpoints
            )

    @property
    def conductor_client(self):
        if self._conductor_client is None:
            target = messaging.Target(
                topic=self.conductor_topic,
                version=self.API_VERSION,
            )
            self._conductor_client = rpc.get_client(
                target,
                serializer=base.WatcherObjectSerializer()
            )
        return self._conductor_client

    @conductor_client.setter
    def conductor_client(self, c):
        self.conductor_client = c

    def build_topic_handler(self, topic_name, endpoints=()):
        target = messaging.Target(
            topic=topic_name,
            # For compatibility, we can override it with 'host' opt
            server=CONF.host or socket.gethostname(),
            version=self.api_version,
        )
        return rpc.get_server(
            target, endpoints,
            serializer=rpc.JsonPayloadSerializer()
        )

    def build_notification_handler(self, topic_names, endpoints=()):
        targets = []
        for topic in topic_names:
            kwargs = {}
            if '.' in topic:
                exchange, topic = topic.split('.')
                kwargs['exchange'] = exchange
            kwargs['topic'] = topic
            targets.append(messaging.Target(**kwargs))

        return rpc.get_notification_listener(
            targets, endpoints,
            serializer=rpc.JsonPayloadSerializer(),
            pool=CONF.host
        )

    def start(self):
        LOG.debug("Connecting to '%s'", CONF.transport_url)
        if self.conductor_topic_handler:
            self.conductor_topic_handler.start()
        if self.notification_handler:
            self.notification_handler.start()
        if self.heartbeat:
            self.heartbeat.start()

    def stop(self):
        LOG.debug("Disconnecting from '%s'", CONF.transport_url)
        if self.conductor_topic_handler:
            self.conductor_topic_handler.stop()
        if self.notification_handler:
            self.notification_handler.stop()
        if self.heartbeat:
            self.heartbeat.stop()

    def reset(self):
        """Reset a service in case it received a SIGHUP."""

    def wait(self):
        """Wait for service to complete."""

    def check_api_version(self, ctx):
        api_manager_version = self.conductor_client.call(
            ctx, 'check_api_version', api_version=self.api_version)
        return api_manager_version


def launch(conf, service_, workers=1, restart_method='mutate'):
    return service.launch(conf, service_, workers, restart_method)


def prepare_service(argv=(), conf=cfg.CONF):
    log.register_options(conf)
    gmr_opts.set_defaults(conf)

    config.parse_args(argv)
    cfg.set_defaults(_options.log_opts,
                     default_log_levels=_DEFAULT_LOG_LEVELS)
    log.setup(conf, 'python-watcher')
    conf.log_opt_values(LOG, log.DEBUG)
    objects.register_all()

    gmr.TextGuruMeditation.register_section(
        _('Plugins'), plugins_conf.show_plugins)
    gmr.TextGuruMeditation.setup_autorun(version, conf=conf)
