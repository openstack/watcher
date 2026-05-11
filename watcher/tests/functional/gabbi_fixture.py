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

from gabbi import fixture as gabbi_fixture

from watcher.tests.functional.base import WatcherEnvironment


class _LazyWsgiApp:
    """WSGI wrapper that defers app creation until the first request.

    Gabbi calls the intercept callable during test discovery (inside
    ``build_tests`` → ``Http.__init__``), before any GabbiFixture has
    had a chance to run ``start_fixture``.  Importing the real Pecan
    app at that point fails because OVO classes are not yet registered.

    This wrapper delays the import and instantiation of
    ``VersionSelectorApplication`` until the WSGI ``__call__`` is
    actually invoked (i.e. during a test request, after the fixture
    has set up the environment).
    """

    def __init__(self):
        self._app = None

    def __call__(self, environ, start_response):
        if self._app is None:
            from watcher.api import app as watcher_app

            self._app = watcher_app.VersionSelectorApplication()
        return self._app(environ, start_response)


def wsgi_app():
    """Return a lazy WSGI application for gabbi intercept."""
    return _LazyWsgiApp()


class WatcherGabbiFixture(gabbi_fixture.GabbiFixture):
    """Set up the full Watcher environment for gabbi tests.

    Starts the decision engine and applier in-process so that
    gabbi YAML tests can exercise the full audit lifecycle.
    """

    def start_fixture(self):
        self.env = WatcherEnvironment(
            start_de=True, start_applier=True, log_name='gabbi'
        )
        self.env.setUp()

    def stop_fixture(self):
        self.env.cleanUp()
