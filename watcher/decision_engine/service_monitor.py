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


import datetime
import itertools
from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

from watcher.common import context as watcher_context
from watcher.common import scheduling
from watcher import notifications

from watcher import objects

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class ServiceMonitoringService(scheduling.BackgroundSchedulerService):
    """Service to monitor the status of Watcher services.

    This service monitors all Watcher services and handles failover
    for continuous audits when decision-engine services fail.
    """

    def __init__(self, gconfig={}, **options):
        self.services_status = {}
        self.last_leader = None
        super().__init__(gconfig, **options)

    def get_services_status(self, context):
        services_states = []
        services = objects.service.Service.list(context)
        for service in services:
            state = self.get_service_status(context, service.id)
            service.state = state
            services_states.append(service)
        return services_states

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

    def _am_i_leader(self, services):
        active_hosts = sorted(
            [service.host for service in services
             if (service.state == objects.service.ServiceStatus.ACTIVE and
                 service.name == 'watcher-decision-engine')])
        if not active_hosts:
            LOG.info("No active decision-engine services found")
            self.last_leader = None
            return False

        leader = active_hosts[0]
        if leader != self.last_leader:
            LOG.info(
                f"Leader election completed: {self.last_leader} -> {leader}. "
                f"Selected as leader: {CONF.host == leader}")
            self.last_leader = leader
        return (CONF.host == leader)

    def monitor_services_status(self, context):
        active_s = objects.service.ServiceStatus.ACTIVE
        failed_s = objects.service.ServiceStatus.FAILED
        services = self.get_services_status(context)
        alive_services = [
            s.host for s in services
            if s.state == active_s and s.name == 'watcher-decision-engine']
        leader = self._am_i_leader(services)
        for service in services:
            result = service.state
            changed = False
            # This covers both a service change, initial service monitor
            # startup and adding a new service
            if self.services_status.get(service.id) != result:
                # Notification is sent only if the service is already monitored
                if self.services_status.get(service.id) is not None:
                    changed = True
                self.services_status[service.id] = result

                if not leader:
                    # Only leader can manage audits failovers
                    # on services status changes
                    continue
                if changed:
                    notifications.service.send_service_update(context, service,
                                                              state=result)
                # Only execute the migration logic if there are alive
                # services
                if len(alive_services) == 0:
                    LOG.warning('No alive services found for decision engine')
                    continue
                if (result == failed_s) and (
                        service.name == 'watcher-decision-engine'):
                    audit_filters = {
                        'audit_type': objects.audit.AuditType.CONTINUOUS.value,
                        'state': objects.audit.State.ONGOING,
                        'hostname': service.host
                    }
                    ongoing_audits = objects.Audit.list(
                        context,
                        filters=audit_filters,
                        eager=True)
                    self._migrate_audits_to_new_host(
                        ongoing_audits, alive_services)

    def get_service_status(self, context, service_id):
        service = objects.Service.get(context, service_id)
        last_heartbeat = (service.last_seen_up or service.updated_at or
                          service.created_at)
        if isinstance(last_heartbeat, str):
            # NOTE(russellb) If this service came in over rpc via
            # conductor, then the timestamp will be a string and needs to be
            # converted back to a datetime.
            last_heartbeat = timeutils.parse_strtime(last_heartbeat)
        else:
            # Objects have proper UTC timezones, but the timeutils comparison
            # below does not (and will fail)
            last_heartbeat = last_heartbeat.replace(tzinfo=None)
        elapsed = timeutils.delta_seconds(last_heartbeat, timeutils.utcnow())
        is_up = abs(elapsed) <= CONF.service_down_time
        if not is_up:
            LOG.warning('Seems service %(name)s on host %(host)s is down. '
                        'Last heartbeat was %(lhb)s. Elapsed time is %(el)s',
                        {'name': service.name,
                         'host': service.host,
                         'lhb': str(last_heartbeat), 'el': str(elapsed)})
            return objects.service.ServiceStatus.FAILED

        return objects.service.ServiceStatus.ACTIVE

    def start(self):
        """Start service."""
        context = watcher_context.make_context(is_admin=True)
        LOG.info('Starting decision-engine service monitoring service')
        self.add_job(self.monitor_services_status,
                     name='service_status', trigger='interval',
                     jobstore='default', args=[context],
                     next_run_time=datetime.datetime.now(),
                     seconds=CONF.periodic_interval)
        super().start()

    def stop(self):
        """Stop service."""
        self.shutdown()

    def wait(self):
        """Wait for service to complete."""

    def reset(self):
        """Reset service.

        Called in case service running in daemon mode receives SIGHUP.
        """
