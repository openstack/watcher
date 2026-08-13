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

import fixtures

from oslo_config import cfg
from oslo_utils.fixture import uuidsentinel
from wsgi_intercept import interceptor

from watcher.api import app as watcher_app


CONF = cfg.CONF


class APIFixture(fixtures.Fixture):
    """Create a Watcher API server as a test fixture.

    Runs the real Pecan WSGI application using wsgi-intercept to
    route HTTP requests in-process without opening a real socket.

    Authentication is disabled; the ContextHook reads X-User-Id,
    X-Project-Id, X-Auth-Token, and X-Roles headers to build a
    RequestContext, matching production behavior without Keystone.
    """

    def __init__(self, api_version='v1'):
        super().__init__()
        self.api_version = api_version

    def setUp(self):
        super().setUp()
        hostname = uuidsentinel.watcher_api_host
        port = 80
        endpoint = 'http://%s:%s/' % (hostname, port)

        CONF.set_override('enable_authentication', False)
        self.addCleanup(CONF.clear_override, 'enable_authentication')

        wsgi_app = watcher_app.VersionSelectorApplication()
        intercept = interceptor.RequestsInterceptor(
            lambda: wsgi_app, url=endpoint
        )
        intercept.install_intercept()
        self.addCleanup(intercept.uninstall_intercept)

        base_url = 'http://%(host)s:%(port)s/%(version)s' % {
            'host': hostname,
            'port': port,
            'version': self.api_version,
        }
        self.endpoint = endpoint
        self.base_url = base_url
