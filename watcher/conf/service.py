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

import socket

from oslo_config import cfg

from watcher._i18n import _

SERVICE_OPTS = [
    cfg.IntOpt('periodic_interval',
               default=60,
               mutable=True,
               help=_('Seconds between running periodic tasks.')),
    cfg.HostAddressOpt('host',
                       default=socket.gethostname(),
                       help=_('Name of this node. This can be an opaque '
                              'identifier. It is not necessarily a hostname, '
                              'FQDN, or IP address. However, the node name '
                              'must be valid within an AMQP key.')
                       ),
    cfg.IntOpt('service_down_time',
               default=90,
               help=_('Maximum time since last check-in for up service.'))
]


def register_opts(conf):
    conf.register_opts(SERVICE_OPTS)


def list_opts():
    return [
        ('DEFAULT', SERVICE_OPTS),
    ]
