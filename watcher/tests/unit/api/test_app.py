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

"""Tests for the Watcher API WSGI application setup."""

from unittest import mock

from oslo_config import cfg
from oslo_middleware import cors
from oslo_middleware import http_proxy_to_wsgi
from oslo_middleware import request_id
from oslo_middleware import tracing

from watcher.api import app
from watcher.api.middleware import parsable_error
from watcher.common import config
from watcher.tests.unit import base


class TestWrapApp(base.TestCase):
    def _middleware_chain(self, wsgi_app):
        """Return the middlewares from the outermost to the innermost."""
        chain = []
        while not isinstance(wsgi_app, mock.Mock):
            chain.append(type(wsgi_app))
            # ParsableErrorMiddleware stores the wrapped app in ``app``,
            # the oslo.middleware filters in ``application``.
            wsgi_app = getattr(wsgi_app, 'application', None) or wsgi_app.app
        return chain

    def test_middleware_chain(self):
        wrapped = app._wrap_app(mock.Mock())

        self.assertEqual(
            [
                cors.CORS,
                http_proxy_to_wsgi.HTTPProxyToWSGI,
                request_id.RequestId,
                tracing.TracingMiddleware,
                parsable_error.ParsableErrorMiddleware,
            ],
            self._middleware_chain(wrapped),
        )

    def test_tracing_disabled_by_default(self):
        wrapped = app._wrap_app(mock.Mock())

        tracing_mw = wrapped.application.application.application
        self.assertIsInstance(tracing_mw, tracing.TracingMiddleware)
        self.assertFalse(cfg.CONF.oslo_middleware_tracing.enabled)
        self.assertFalse(tracing_mw._tracing_enabled)


class TestTracingDefaults(base.TestCase):
    def test_service_name_default(self):
        config.set_lib_defaults()
        # The tracing options are registered by the middleware itself.
        app._wrap_app(mock.Mock())

        self.assertEqual(
            'watcher-api', cfg.CONF.oslo_middleware_tracing.service_name
        )
