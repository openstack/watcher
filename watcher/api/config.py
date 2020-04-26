# -*- encoding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg
from watcher.api import hooks

# Server Specific Configurations
# See https://pecan.readthedocs.org/en/latest/configuration.html#server-configuration # noqa
server = {
    'port': '9322',
    'host': '127.0.0.1'
}

# Pecan Application Configurations
# See https://pecan.readthedocs.org/en/latest/configuration.html#application-configuration # noqa
acl_public_routes = ['/']
if not cfg.CONF.api.get("enable_webhooks_auth"):
    acl_public_routes.append('/v1/webhooks/.*')

app = {
    'root': 'watcher.api.controllers.root.RootController',
    'modules': ['watcher.api'],
    'hooks': [
        hooks.ContextHook(),
        hooks.NoExceptionTracebackHook(),
    ],
    'static_root': '%(confdir)s/public',
    'enable_acl': True,
    'acl_public_routes': acl_public_routes,
}

# WSME Configurations
# See https://wsme.readthedocs.org/en/latest/integrate.html#configuration
wsme = {
    'debug': cfg.CONF.get("debug") if "debug" in cfg.CONF else False,
}

PECAN_CONFIG = {
    "server": server,
    "app": app,
    "wsme": wsme,
}
