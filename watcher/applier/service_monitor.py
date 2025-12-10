# Copyright (c) 2025 Red Hat, Inc.
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
from oslo_log import log

from watcher.applier import rpcapi
from watcher.applier import sync
from watcher.common import service
from watcher import notifications

from watcher import objects

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class ApplierMonitor(service.ServiceMonitoringBase):
    """Service to monitor the status of Watcher Applier services.

    This service monitors the Watcher Applier services and handles failover
    for action plans when applier services fail.
    """

    def __init__(self, gconfig={}, **options):
        super().__init__('watcher-applier', gconfig, **options)
        self.applier_client = rpcapi.ApplierAPI()

    def _retrigger_pending_actionplans(self, context, host):
        """Unassign and retrigger pending action plans on a failed host."""

        pending_actionplans = objects.ActionPlan.list(
            context,
            filters={'state': objects.action_plan.State.PENDING,
                     'hostname': host},
            eager=True)
        for actionplan in pending_actionplans:
            LOG.warning("Retriggering action plan %s in Pending state on "
                        "failed host %s", actionplan.uuid, host)
            actionplan.hostname = None
            actionplan.save()
            self.applier_client.launch_action_plan(context, actionplan.uuid)

    def monitor_services_status(self, context):
        failed_s = objects.service.ServiceStatus.FAILED
        services = self.get_services_status(context)
        leader = self._am_i_leader(services)
        for watcher_service in services:
            result = watcher_service.state
            # This covers both a service change, initial service monitor
            # startup and adding a new service
            if self.services_status.get(watcher_service.id) != result:
                changed = False
                # Notification is sent only if the service is already
                # monitored
                if self.services_status.get(watcher_service.id) is not None:
                    changed = True
                self.services_status[watcher_service.id] = result

                if not leader:
                    # Only leader can manage action plans failovers
                    # on services status changes
                    continue
                if changed:
                    notifications.service.send_service_update(context,
                                                              watcher_service,
                                                              state=result)
                if result == failed_s:
                    # Cancel ongoing action plans on the failed service using
                    # the existing startup sync method
                    syncer = sync.Syncer()
                    syncer._cancel_ongoing_actionplans(context,
                                                       watcher_service.host)
                    # Pending action plans should be unassigned and
                    # re-triggered
                    self._retrigger_pending_actionplans(context,
                                                        watcher_service.host)
