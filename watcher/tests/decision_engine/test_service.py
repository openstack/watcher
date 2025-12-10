# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

from watcher.common import service as watcher_service
from watcher.decision_engine.audit import continuous as c_handler
from watcher.decision_engine import scheduling
from watcher.decision_engine import service
from watcher.decision_engine import service_monitor
from watcher.tests import base


@mock.patch.object(service_monitor.DecisionEngineMonitor, '__init__',
                   return_value=None)
@mock.patch.object(scheduling.DecisionEngineSchedulingService, '__init__',
                   return_value=None)
@mock.patch.object(watcher_service.Service, '__init__', return_value=None)
class TestDecisionEngineService(base.TestCase):

    @mock.patch.object(service_monitor.DecisionEngineMonitor, 'start')
    @mock.patch.object(c_handler.ContinuousAuditHandler, 'start')
    @mock.patch.object(scheduling.DecisionEngineSchedulingService, 'start')
    @mock.patch.object(watcher_service.Service, 'start')
    def test_decision_engine_service_start(self, svc_start, sch_start,
                                           cont_audit_start, svc_mon_start,
                                           svc_init, sch_init, svc_mon_init):
        de_service = service.DecisionEngineService()
        de_service.start()
        # Creates an DecisionEngineSchedulingService instance
        self.assertIsInstance(de_service.bg_scheduler,
                              scheduling.DecisionEngineSchedulingService)
        # Creates a DecisionEngineMonitor instance
        self.assertIsInstance(de_service.service_monitor,
                              service_monitor.DecisionEngineMonitor)

        svc_start.assert_called()
        sch_start.assert_called()
        cont_audit_start.assert_called()
        svc_mon_start.assert_called()

    @mock.patch.object(service_monitor.DecisionEngineMonitor, 'stop')
    @mock.patch.object(scheduling.DecisionEngineSchedulingService, 'stop')
    @mock.patch.object(watcher_service.Service, 'stop')
    def test_decision_engine_service_stop(self, svc_stop, sch_stop,
                                          svc_mon_stop, svc_init, sch_init,
                                          svc_mon_init):
        de_service = service.DecisionEngineService()
        de_service.stop()

        svc_stop.assert_called()
        sch_stop.assert_called()
        svc_mon_stop.assert_called()

    @mock.patch.object(service_monitor.DecisionEngineMonitor, 'wait')
    @mock.patch.object(scheduling.DecisionEngineSchedulingService, 'wait')
    @mock.patch.object(watcher_service.Service, 'wait')
    def test_decision_engine_service_wait(self, svc_wait, sch_wait,
                                          svc_mon_wait, svc_init, sch_init,
                                          svc_mon_init):
        de_service = service.DecisionEngineService()
        de_service.wait()

        svc_wait.assert_called()
        sch_wait.assert_called()
        svc_mon_wait.assert_called()

    @mock.patch.object(service_monitor.DecisionEngineMonitor, 'reset')
    @mock.patch.object(scheduling.DecisionEngineSchedulingService, 'reset')
    @mock.patch.object(watcher_service.Service, 'reset')
    def test_decision_engine_service_reset(self, svc_reset, sch_reset,
                                           svc_mon_reset, svc_init, sch_init,
                                           svc_mon_init):
        de_service = service.DecisionEngineService()
        de_service.reset()

        svc_reset.assert_called()
        sch_reset.assert_called()
        svc_mon_reset.assert_called()
