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

import logging
import socket

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import _options
from oslo_log import log
import oslo_messaging as om
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts
from oslo_service import service
from oslo_service import wsgi

from watcher._i18n import _
from watcher.api import app
from watcher.common import config
from watcher.common.messaging.events import event_dispatcher as dispatcher
from watcher.common.messaging import messaging_handler
from watcher.common import rpc
from watcher.objects import base
from watcher import opts
from watcher import version

service_opts = [
    cfg.IntOpt('periodic_interval',
               default=60,
               help=_('Seconds between running periodic tasks.')),
    cfg.StrOpt('host',
               default=socket.getfqdn(),
               help=_('Name of this node. This can be an opaque identifier.  '
                      'It is not necessarily a hostname, FQDN, or IP address. '
                      'However, the node name must be valid within '
                      'an AMQP key, and if using ZeroMQ, a valid '
                      'hostname, FQDN, or IP address.')),
]

cfg.CONF.register_opts(service_opts)

CONF = cfg.CONF
LOG = log.getLogger(__name__)

_DEFAULT_LOG_LEVELS = ['amqp=WARN', 'amqplib=WARN', 'qpid.messaging=INFO',
                       'oslo.messaging=INFO', 'sqlalchemy=WARN',
                       'keystoneclient=INFO', 'stevedore=INFO',
                       'eventlet.wsgi.server=WARN', 'iso8601=WARN',
                       'paramiko=WARN', 'requests=WARN', 'neutronclient=WARN',
                       'glanceclient=WARN', 'watcher.openstack.common=WARN']


class WSGIService(service.ServiceBase):
    """Provides ability to launch Watcher API from wsgi app."""

    def __init__(self, name, use_ssl=False):
        """Initialize, but do not start the WSGI server.

        :param name: The name of the WSGI server given to the loader.
        :param use_ssl: Wraps the socket in an SSL context if True.
        """
        self.name = name
        self.app = app.VersionSelectorApplication()
        self.workers = (CONF.api.workers or
                        processutils.get_worker_count())
        self.server = wsgi.Server(CONF, name, self.app,
                                  host=CONF.api.host,
                                  port=CONF.api.port,
                                  use_ssl=use_ssl,
                                  logger_name=name)

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


class Service(service.ServiceBase, dispatcher.EventDispatcher):

    API_VERSION = '1.0'

    def __init__(self, manager_class):
        super(Service, self).__init__()
        self.manager = manager_class()

        self.publisher_id = self.manager.publisher_id
        self.api_version = self.manager.API_VERSION
        self.conductor_topic = self.manager.conductor_topic
        self.status_topic = self.manager.status_topic

        self.conductor_endpoints = [
            ep(self) for ep in self.manager.conductor_endpoints
        ]
        self.status_endpoints = [
            ep(self.publisher_id) for ep in self.manager.status_endpoints
        ]

        self.serializer = rpc.RequestContextSerializer(
            base.WatcherObjectSerializer())

        self.conductor_topic_handler = self.build_topic_handler(
            self.conductor_topic, self.conductor_endpoints)
        self.status_topic_handler = self.build_topic_handler(
            self.status_topic, self.status_endpoints)

        self._conductor_client = None
        self._status_client = None

    @property
    def conductor_client(self):
        if self._conductor_client is None:
            transport = om.get_transport(CONF)
            target = om.Target(
                topic=self.conductor_topic,
                version=self.API_VERSION,
            )
            self._conductor_client = om.RPCClient(
                transport, target, serializer=self.serializer)
        return self._conductor_client

    @conductor_client.setter
    def conductor_client(self, c):
        self.conductor_client = c

    @property
    def status_client(self):
        if self._status_client is None:
            transport = om.get_transport(CONF)
            target = om.Target(
                topic=self.status_topic,
                version=self.API_VERSION,
            )
            self._status_client = om.RPCClient(
                transport, target, serializer=self.serializer)
        return self._status_client

    @status_client.setter
    def status_client(self, c):
        self.status_client = c

    def build_topic_handler(self, topic_name, endpoints=()):
        return messaging_handler.MessagingHandler(
            self.publisher_id, topic_name, [self.manager] + list(endpoints),
            self.api_version, self.serializer)

    def start(self):
        LOG.debug("Connecting to '%s' (%s)",
                  CONF.transport_url, CONF.rpc_backend)
        self.conductor_topic_handler.start()
        self.status_topic_handler.start()

    def stop(self):
        LOG.debug("Disconnecting from '%s' (%s)",
                  CONF.transport_url, CONF.rpc_backend)
        self.conductor_topic_handler.stop()
        self.status_topic_handler.stop()

    def reset(self):
        """Reset a service in case it received a SIGHUP."""

    def wait(self):
        """Wait for service to complete."""

    def publish_control(self, event, payload):
        return self.conductor_topic_handler.publish_event(event, payload)

    def publish_status(self, event, payload, request_id=None):
        return self.status_topic_handler.publish_event(
            event, payload, request_id)

    def get_version(self):
        return self.api_version

    def check_api_version(self, context):
        api_manager_version = self.conductor_client.call(
            context.to_dict(), 'check_api_version',
            api_version=self.api_version)
        return api_manager_version

    def response(self, evt, ctx, message):
        payload = {
            'request_id': ctx['request_id'],
            'msg': message
        }
        self.publish_status(evt, payload)


def process_launcher(conf=cfg.CONF):
    return service.ProcessLauncher(conf)


def prepare_service(argv=(), conf=cfg.CONF):
    log.register_options(conf)
    gmr_opts.set_defaults(conf)

    config.parse_args(argv)
    cfg.set_defaults(_options.log_opts,
                     default_log_levels=_DEFAULT_LOG_LEVELS)
    log.setup(conf, 'python-watcher')
    conf.log_opt_values(LOG, logging.DEBUG)

    gmr.TextGuruMeditation.register_section(_('Plugins'), opts.show_plugins)
    gmr.TextGuruMeditation.setup_autorun(version)
