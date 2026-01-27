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

from watcher.applier import manager
from watcher.applier import service_monitor
from watcher.common import service as watcher_service


class ApplierService(watcher_service.Service):
    """Applier Service that runs on a host.

    The applier service holds a RPC server, a notification
    listener server, a heartbeat service, and a service monitoring service.
    """

    def __init__(self):
        super().__init__(manager.ApplierManager)
        self._service_monitor = None

    @property
    def service_monitor(self):
        if self._service_monitor is None:
            self._service_monitor = service_monitor.ApplierMonitor()
        return self._service_monitor

    def start(self):
        """Start service."""
        super().start()
        self.service_monitor.start()

    def stop(self):
        """Stop service."""
        super().stop()
        self.service_monitor.stop()

    def wait(self):
        """Wait for service to complete."""
        super().wait()
        self.service_monitor.wait()

    def reset(self):
        """Reset service."""
        super().reset()
        self.service_monitor.reset()
