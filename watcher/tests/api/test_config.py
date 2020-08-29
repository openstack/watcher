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

import importlib
from oslo_config import cfg
from watcher.api import config as api_config
from watcher.tests.api import base


class TestRoot(base.FunctionalTest):

    def test_config_enable_webhooks_auth(self):
        acl_public_routes = ['/']
        cfg.CONF.set_override('enable_webhooks_auth', True, 'api')
        importlib.reload(api_config)
        self.assertEqual(acl_public_routes,
                         api_config.app['acl_public_routes'])

    def test_config_disable_webhooks_auth(self):
        acl_public_routes = ['/', '/v1/webhooks/.*']
        cfg.CONF.set_override('enable_webhooks_auth', False, 'api')
        importlib.reload(api_config)
        self.assertEqual(acl_public_routes,
                         api_config.app['acl_public_routes'])
