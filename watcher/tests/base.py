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

"""Common base test class for all Watcher tests (unit and functional)."""

import fixtures
import testscenarios

from oslo_config import cfg
from oslotest import base

from watcher.tests.local_fixtures import watcher as watcher_fixtures


CONF = cfg.CONF


class WatcherBaseTestCase(testscenarios.WithScenarios, base.BaseTestCase):
    """Root base class for all Watcher tests.

    Provides helpers shared by both unit tests and functional tests.
    """

    def setUp(self):
        # Disable oslotest's ConfigureLogging fixture — we use our
        # own StandardLogging which does not interfere with oslo_log.
        with fixtures.EnvironmentVariable('OS_LOG_CAPTURE', '0'):
            super().setUp()
        self.stdlog = self.useFixture(watcher_fixtures.StandardLogging())
        self.addCleanup(cfg.CONF.reset)

    def flags(self, **kw):
        """Override config flags for the duration of a test.

        Original values are restored automatically on cleanup.

        Example::

            self.flags(periodic_interval=10, group='watcher_decision_engine')
        """
        group = kw.pop('group', None)
        for k, v in kw.items():
            CONF.set_override(k, v, group)
            self.addCleanup(CONF.clear_override, k, group)
