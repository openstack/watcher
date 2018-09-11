# -*- encoding: utf-8 -*-

# Copyright © 2012 New Dream Network, LLC (DreamHost)
# All Rights Reserved.
# Copyright (c) 2016 Intel Corp
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


import pecan

from watcher.api import acl
from watcher.api import config as api_config
from watcher.api.middleware import parsable_error
from watcher import conf

CONF = conf.CONF


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
        wrap_app=parsable_error.ParsableErrorMiddleware,
        **app_conf
    )

    return acl.install(app, CONF, config.app.acl_public_routes)


class VersionSelectorApplication(object):
    def __init__(self):
        pc = get_pecan_config()
        self.v1 = setup_app(config=pc)

    def __call__(self, environ, start_response):
        return self.v1(environ, start_response)
