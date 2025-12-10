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

from watcher.common import service as watcher_service
from watcher.decision_engine.audit import continuous as c_handler
from watcher.decision_engine import manager
from watcher.decision_engine import scheduling
from watcher.decision_engine import service_monitor


class DecisionEngineService(watcher_service.Service):
    """Decision Engine Service that runs on a host.

    The decision engine service holds a RPC server, a notification
    listener server, a heartbeat service, starts a background scheduling
    service to run watcher periodic jobs, and a service monitoring service.
    """

    def __init__(self):
        super().__init__(manager.DecisionEngineManager)
        # Background scheduler starts the cluster model collector periodic
        # task, an one shot task to cancel ongoing audits and a periodic
        # check for expired action plans
        self._bg_scheduler = None
        self._continuous_handler = None
        self._service_monitor = None

    @property
    def bg_scheduler(self):
        if self._bg_scheduler is None:
            self._bg_scheduler = scheduling.DecisionEngineSchedulingService()
        return self._bg_scheduler

    @property
    def continuous_handler(self):
        if self._continuous_handler is None:
            self._continuous_handler = c_handler.ContinuousAuditHandler()
        return self._continuous_handler

    @property
    def service_monitor(self):
        if self._service_monitor is None:
            self._service_monitor = service_monitor.DecisionEngineMonitor()
        return self._service_monitor

    def start(self):
        """Start service."""
        super().start()
        self.bg_scheduler.start()
        self.continuous_handler.start()
        self.service_monitor.start()

    def stop(self):
        """Stop service."""
        super().stop()
        self.bg_scheduler.stop()
        self.service_monitor.stop()

    def wait(self):
        """Wait for service to complete."""
        super().wait()
        self.bg_scheduler.wait()
        self.service_monitor.wait()

    def reset(self):
        """Reset service."""
        super().reset()
        self.bg_scheduler.reset()
        self.service_monitor.reset()
