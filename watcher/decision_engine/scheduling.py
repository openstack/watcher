# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

import eventlet
from oslo_log import log

from watcher.common import context
from watcher.common import exception
from watcher.common import scheduling

from watcher.decision_engine.model.collector import manager
from watcher import objects

from watcher import conf

LOG = log.getLogger(__name__)
CONF = conf.CONF


class DecisionEngineSchedulingService(scheduling.BackgroundSchedulerService):

    def __init__(self, gconfig=None, **options):
        gconfig = None or {}
        super(DecisionEngineSchedulingService, self).__init__(
            gconfig, **options)
        self.collector_manager = manager.CollectorManager()

    @property
    def collectors(self):
        return self.collector_manager.get_collectors()

    def add_sync_jobs(self):
        for name, collector in self.collectors.items():
            timed_task = self._wrap_collector_sync_with_timeout(
                collector, name)
            self.add_job(timed_task,
                         trigger='interval',
                         seconds=collector.config.period,
                         next_run_time=datetime.datetime.now())

    def _as_timed_sync_func(self, sync_func, name, timeout):
        def _timed_sync():
            with eventlet.Timeout(
                timeout,
                exception=exception.ClusterDataModelCollectionError(cdm=name)
            ):
                sync_func()

        return _timed_sync

    def _wrap_collector_sync_with_timeout(self, collector, name):
        """Add an execution timeout constraint on a function"""
        timeout = collector.config.period

        def _sync():
            try:
                timed_sync = self._as_timed_sync_func(
                    collector.synchronize, name, timeout)
                timed_sync()
            except Exception as exc:
                LOG.exception(exc)
                collector.set_cluster_data_model_as_stale()

        return _sync

    def add_checkstate_job(self):
        # 30 minutes interval
        interval = CONF.watcher_decision_engine.check_periodic_interval
        ap_manager = objects.action_plan.StateManager()
        if CONF.watcher_decision_engine.action_plan_expiry != 0:
            self.add_job(ap_manager.check_expired, 'interval',
                         args=[context.make_context()],
                         seconds=interval,
                         next_run_time=datetime.datetime.now())

    def cancel_ongoing_audits(self):
        audit_filters = {
            'audit_type': objects.audit.AuditType.ONESHOT.value,
            'state': objects.audit.State.ONGOING,
            'hostname': CONF.host
        }
        local_context = context.make_context()
        ongoing_audits = objects.Audit.list(
            local_context,
            filters=audit_filters)
        for audit in ongoing_audits:
            audit.state = objects.audit.State.CANCELLED
            audit.save()
            LOG.info("Audit %(uuid)s has been cancelled because it was in "
                     "%(state)s state when Decision Engine had been stopped "
                     "on %(hostname)s host.",
                     {'uuid': audit.uuid,
                      'state': objects.audit.State.ONGOING,
                      'hostname': audit.hostname})

    def start(self):
        """Start service."""
        self.add_sync_jobs()
        self.add_checkstate_job()
        self.cancel_ongoing_audits()
        super(DecisionEngineSchedulingService, self).start()

    def stop(self):
        """Stop service."""
        self.shutdown()

    def wait(self):
        """Wait for service to complete."""

    def reset(self):
        """Reset service.

        Called in case service running in daemon mode receives SIGHUP.
        """
