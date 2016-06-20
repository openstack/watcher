# -*- encoding: utf-8 -*-

# Copyright © 2012 New Dream Network, LLC (DreamHost)
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


from oslo_config import cfg
import pecan

from watcher._i18n import _
from watcher.api import acl
from watcher.api import config as api_config
from watcher.api import middleware

# Register options for the service
API_SERVICE_OPTS = [
    cfg.PortOpt('port',
                default=9322,
                help=_('The port for the watcher API server')),
    cfg.StrOpt('host',
               default='127.0.0.1',
               help=_('The listen IP for the watcher API server')),
    cfg.IntOpt('max_limit',
               default=1000,
               help=_('The maximum number of items returned in a single '
                      'response from a collection resource')),
    cfg.IntOpt('workers',
               min=1,
               help=_('Number of workers for Watcher API service. '
                      'The default is equal to the number of CPUs available '
                      'if that can be determined, else a default worker '
                      'count of 1 is returned.')),

    cfg.BoolOpt('enable_ssl_api',
                default=False,
                help=_("Enable the integrated stand-alone API to service "
                       "requests via HTTPS instead of HTTP. If there is a "
                       "front-end service performing HTTPS offloading from "
                       "the service, this option should be False; note, you "
                       "will want to change public API endpoint to represent "
                       "SSL termination URL with 'public_endpoint' option.")),
]

CONF = cfg.CONF
opt_group = cfg.OptGroup(name='api',
                         title='Options for the watcher-api service')

CONF.register_group(opt_group)
CONF.register_opts(API_SERVICE_OPTS, opt_group)


def get_pecan_config():
    # Set up the pecan configuration
    return pecan.configuration.conf_from_dict(api_config.PECAN_CONFIG)


def setup_app(config=None):
    if not config:
        config = get_pecan_config()

    app_conf = dict(config.app)

    app = pecan.make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        debug=CONF.debug,
        wrap_app=middleware.ParsableErrorMiddleware,
        **app_conf
    )

    return acl.install(app, CONF, config.app.acl_public_routes)


class VersionSelectorApplication(object):
    def __init__(self):
        pc = get_pecan_config()
        self.v1 = setup_app(config=pc)

    def __call__(self, environ, start_response):
        return self.v1(environ, start_response)
