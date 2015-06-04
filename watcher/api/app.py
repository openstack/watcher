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

from watcher.api import acl
from watcher.api import config as api_config
from watcher.api import middleware
from watcher.decision_engine.framework.strategy import strategy_selector

# Register options for the service
API_SERVICE_OPTS = [
    cfg.IntOpt('port',
               default=9322,
               help='The port for the watcher API server'),
    cfg.StrOpt('host',
               default='0.0.0.0',
               help='The listen IP for the watcher API server'),
    cfg.IntOpt('max_limit',
               default=1000,
               help='The maximum number of items returned in a single '
                    'response from a collection resource.')
]

CONF = cfg.CONF
opt_group = cfg.OptGroup(name='api',
                         title='Options for the watcher-api service')

CONF.register_group(opt_group)
CONF.register_opts(API_SERVICE_OPTS, opt_group)
CONF.register_opts(strategy_selector.WATCHER_GOALS_OPTS)


def get_pecan_config():
    # Set up the pecan configuration
    filename = api_config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


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
