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

from unittest import mock

import fixtures

from watcher.applier import manager as applier_manager
from watcher.common import service as watcher_service
from watcher.decision_engine import manager as de_manager


SERVICE_MANAGERS = {
    'watcher-decision-engine': de_manager.DecisionEngineManager,
    'watcher-applier': applier_manager.ApplierManager,
}


class ServiceFixture(fixtures.Fixture):
    """Run a Watcher service in-process as a test fixture.

    Starts the base Service class (not DecisionEngineService or
    ApplierService) to avoid background schedulers, continuous audit
    handlers, and service monitors that are not needed in Phase 1
    functional tests.

    ServiceHeartbeat is mocked out because its __init__ calls
    send_beat() which writes to the DB.
    """

    def __init__(self, name, host=None):
        super().__init__()
        self.name = name
        self.host = host or 'test-host'

    def setUp(self):
        super().setUp()
        manager_class = SERVICE_MANAGERS[self.name]
        with mock.patch.object(
            watcher_service, 'ServiceHeartbeat', autospec=True
        ):
            self.service = watcher_service.Service(manager_class)
        self.service.start()
        self.addCleanup(self._stop_service)

    def _stop_service(self):
        self.service.stop()
        self.service.wait()
