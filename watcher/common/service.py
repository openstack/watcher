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
from oslo_reports import opts as gmr_opts
from oslo_service import service
from oslo_service import wsgi

from watcher._i18n import _
from watcher.api import app
from watcher.common import config


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
