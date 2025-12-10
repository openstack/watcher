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

from watcher.applier import service
from watcher.applier import service_monitor
from watcher.common import service as watcher_service
from watcher.tests.unit import base


@mock.patch.object(service_monitor.ApplierMonitor, '__init__',
                   return_value=None)
@mock.patch.object(watcher_service.Service, '__init__', return_value=None)
class TestApplierService(base.TestCase):

    @mock.patch.object(service_monitor.ApplierMonitor, 'start')
    @mock.patch.object(watcher_service.Service, 'start')
    def test_applier_service_start(self, svc_start, svc_mon_start,
                                   svc_init, svc_mon_init):
        ap_service = service.ApplierService()
        ap_service.start()

        # Creates a DecisionEngineMonitor instance
        self.assertIsInstance(ap_service.service_monitor,
                              service_monitor.ApplierMonitor)

        svc_start.assert_called()
        svc_mon_start.assert_called()

    @mock.patch.object(service_monitor.ApplierMonitor, 'stop')
    @mock.patch.object(watcher_service.Service, 'stop')
    def test_applier_service_stop(self, svc_stop, svc_mon_stop,
                                  svc_init, svc_mon_init):
        ap_service = service.ApplierService()
        ap_service.stop()

        svc_stop.assert_called()
        svc_mon_stop.assert_called()

    @mock.patch.object(service_monitor.ApplierMonitor, 'wait')
    @mock.patch.object(watcher_service.Service, 'wait')
    def test_applier_service_wait(self, svc_wait, svc_mon_wait,
                                  svc_init, svc_mon_init):
        ap_service = service.ApplierService()
        ap_service.wait()

        svc_wait.assert_called()
        svc_mon_wait.assert_called()

    @mock.patch.object(service_monitor.ApplierMonitor, 'reset')
    @mock.patch.object(watcher_service.Service, 'reset')
    def test_applier_service_reset(self, svc_reset, svc_mon_reset,
                                   svc_init, svc_mon_init):
        ap_service = service.ApplierService()
        ap_service.reset()

        svc_reset.assert_called()
        svc_mon_reset.assert_called()
