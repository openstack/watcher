# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Starter script for the Watcher API service."""

import sys

from oslo_config import cfg
from oslo_log import log

from watcher.api import scheduling
from watcher.common import service
from watcher import conf

LOG = log.getLogger(__name__)
CONF = conf.CONF


def main():
    service.prepare_service(sys.argv, CONF)

    host, port = cfg.CONF.api.host, cfg.CONF.api.port
    protocol = "http" if not CONF.api.enable_ssl_api else "https"
    # Build and start the WSGI app
    server = service.WSGIService('watcher-api', CONF.api.enable_ssl_api)

    if host == '127.0.0.1':
        LOG.info('serving on 127.0.0.1:%(port)s, '
                 'view at %(protocol)s://127.0.0.1:%(port)s',
                 dict(protocol=protocol, port=port))
    else:
        LOG.info('serving on %(protocol)s://%(host)s:%(port)s',
                 dict(protocol=protocol, host=host, port=port))

    api_schedule = scheduling.APISchedulingService()
    api_schedule.start()

    launcher = service.launch(CONF, server, workers=server.workers)
    launcher.wait()
