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

import logging as std_logging
import os
from wsgiref import simple_server

from oslo_config import cfg

from watcher.api import app as api_app
from watcher.common.i18n import _
from watcher.openstack.common import log as logging
from watcher import service


LOG = logging.getLogger(__name__)


def main():
    service.prepare_service()

    app = api_app.setup_app()

    # Create the WSGI server and start it
    host, port = cfg.CONF.api.host, cfg.CONF.api.port
    srv = simple_server.make_server(host, port, app)

    logging.setup('watcher')
    LOG.info(_('Starting server in PID %s') % os.getpid())
    LOG.debug("Watcher configuration:")
    cfg.CONF.log_opt_values(LOG, std_logging.DEBUG)

    if host == '0.0.0.0':
        LOG.info(_('serving on 0.0.0.0:%(port)s, '
                   'view at http://127.0.0.1:%(port)s') %
                 dict(port=port))
    else:
        LOG.info(_('serving on http://%(host)s:%(port)s') %
                 dict(host=host, port=port))

    srv.serve_forever()
