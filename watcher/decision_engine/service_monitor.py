# Copyright (c) 2017 Servionica
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


import itertools
from oslo_config import cfg
from oslo_log import log

from watcher.common import service
from watcher import notifications

from watcher import objects

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class DecisionEngineMonitor(service.ServiceMonitoringBase):
    """Service to monitor the status of Watcher services.

    This service monitors all Watcher services and handles failover
    for continuous audits when decision-engine services fail.
    """

    def __init__(self, gconfig={}, **options):
        super().__init__('watcher-decision-engine', gconfig, **options)

    def _migrate_audits_to_new_host(self, ongoing_audits, alive_services):
        round_robin = itertools.cycle(alive_services)
        for audit in ongoing_audits:
            failed_host = audit.hostname
            audit.hostname = round_robin.__next__()
            audit.save()
            LOG.info('Audit %(audit)s has been migrated to '
                     '%(host)s since %(failed_host)s is in'
                     ' %(state)s',
                     {'audit': audit.uuid,
                      'host': audit.hostname,
                      'failed_host': failed_host,
                      'state': objects.service.ServiceStatus.FAILED})

    def monitor_services_status(self, context):
        active_s = objects.service.ServiceStatus.ACTIVE
        failed_s = objects.service.ServiceStatus.FAILED
        services = self.get_services_status(context)
        alive_services = [
            s.host for s in services if s.state == active_s]
        leader = self._am_i_leader(services)
        for watcher_service in services:
            result = watcher_service.state
            changed = False
            # This covers both a service change, initial service monitor
            # startup and adding a new service
            if self.services_status.get(watcher_service.id) != result:
                # Notification is sent only if the service is already monitored
                if self.services_status.get(watcher_service.id) is not None:
                    changed = True
                self.services_status[watcher_service.id] = result

                if not leader:
                    # Only leader can manage audits failovers
                    # on services status changes
                    continue
                if changed:
                    notifications.service.send_service_update(
                        context, watcher_service, state=result)
                # Only execute the migration logic if there are alive
                # services
                if len(alive_services) == 0:
                    LOG.warning('No alive services found for decision engine')
                    continue
                if result == failed_s:
                    audit_filters = {
                        'audit_type': objects.audit.AuditType.CONTINUOUS.value,
                        'state': objects.audit.State.ONGOING,
                        'hostname': watcher_service.host
                    }
                    ongoing_audits = objects.Audit.list(
                        context,
                        filters=audit_filters,
                        eager=True)
                    self._migrate_audits_to_new_host(
                        ongoing_audits, alive_services)
