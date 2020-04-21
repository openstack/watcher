# -*- encoding: utf-8 -*-
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


class APISchedulingService(scheduling.BackgroundSchedulerService):

    def __init__(self, gconfig={}, **options):
        self.services_status = {}
        super(APISchedulingService, self).__init__(gconfig, **options)

    def get_services_status(self, context):
        services = objects.service.Service.list(context)
        active_s = objects.service.ServiceStatus.ACTIVE
        failed_s = objects.service.ServiceStatus.FAILED
        for service in services:
            result = self.get_service_status(context, service.id)
            if service.id not in self.services_status:
                self.services_status[service.id] = result
                continue
            if self.services_status[service.id] != result:
                self.services_status[service.id] = result
                notifications.service.send_service_update(context, service,
                                                          state=result)
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
                    alive_services = [
                        s.host for s in services
                        if (self.services_status[s.id] == active_s and
                            s.name == 'watcher-decision-engine')]

                    round_robin = itertools.cycle(alive_services)
                    for audit in ongoing_audits:
                        audit.hostname = round_robin.__next__()
                        audit.save()
                        LOG.info('Audit %(audit)s has been migrated to '
                                 '%(host)s since %(failed_host)s is in'
                                 ' %(state)s',
                                 {'audit': audit.uuid,
                                  'host': audit.hostname,
                                  'failed_host': service.host,
                                  'state': failed_s})

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
        self.add_job(self.get_services_status, name='service_status',
                     trigger='interval', jobstore='default', args=[context],
                     next_run_time=datetime.datetime.now(),
                     seconds=CONF.periodic_interval)
        super(APISchedulingService, self).start()

    def stop(self):
        """Stop service."""
        self.shutdown()

    def wait(self):
        """Wait for service to complete."""

    def reset(self):
        """Reset service.

        Called in case service running in daemon mode receives SIGHUP.
        """
