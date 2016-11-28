# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica LTD
# Copyright (c) 2016 Intel Corp
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
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

from apscheduler.schedulers import background

from watcher.common import context
from watcher.decision_engine.audit import base
from watcher import objects

from watcher import conf

CONF = conf.CONF


class ContinuousAuditHandler(base.AuditHandler):
    def __init__(self, messaging):
        super(ContinuousAuditHandler, self).__init__(messaging)
        self._scheduler = None
        self.jobs = []
        self._start()
        self.context_show_deleted = context.RequestContext(is_admin=True,
                                                           show_deleted=True)

    @property
    def scheduler(self):
        if self._scheduler is None:
            self._scheduler = background.BackgroundScheduler()
        return self._scheduler

    def _is_audit_inactive(self, audit):
        audit = objects.Audit.get_by_uuid(
            self.context_show_deleted, audit.uuid)
        if audit.state in (objects.audit.State.CANCELLED,
                           objects.audit.State.DELETED,
                           objects.audit.State.FAILED):
            # if audit isn't in active states, audit's job must be removed to
            # prevent using of inactive audit in future.
            job_to_delete = [job for job in self.jobs
                             if list(job.keys())[0] == audit.uuid][0]
            self.jobs.remove(job_to_delete)
            job_to_delete[audit.uuid].remove()

            return True

        return False

    def do_execute(self, audit, request_context):
        # execute the strategy
        solution = self.strategy_context.execute_strategy(
            audit, request_context)

        if audit.audit_type == objects.audit.AuditType.CONTINUOUS.value:
            a_plan_filters = {'audit_uuid': audit.uuid,
                              'state': objects.action_plan.State.RECOMMENDED}
            action_plans = objects.ActionPlan.list(
                request_context, filters=a_plan_filters)
            for plan in action_plans:
                plan.state = objects.action_plan.State.CANCELLED
                plan.save()
        return solution

    def execute_audit(self, audit, request_context):
        if not self._is_audit_inactive(audit):
            self.execute(audit, request_context)

    def launch_audits_periodically(self):
        audit_context = context.RequestContext(is_admin=True)
        audit_filters = {
            'audit_type': objects.audit.AuditType.CONTINUOUS.value,
            'state__in': (objects.audit.State.PENDING,
                          objects.audit.State.ONGOING,
                          objects.audit.State.SUCCEEDED)
        }
        audits = objects.Audit.list(
            audit_context, filters=audit_filters, eager=True)
        scheduler_job_args = [job.args for job in self.scheduler.get_jobs()
                              if job.name == 'execute_audit']
        for audit in audits:
            if audit.uuid not in [arg[0].uuid for arg in scheduler_job_args]:
                job = self.scheduler.add_job(
                    self.execute_audit, 'interval',
                    args=[audit, audit_context],
                    seconds=audit.interval,
                    name='execute_audit',
                    next_run_time=datetime.datetime.now())
                self.jobs.append({audit.uuid: job})

    def _start(self):
        self.scheduler.add_job(
            self.launch_audits_periodically,
            'interval',
            seconds=CONF.watcher_decision_engine.continuous_audit_interval,
            next_run_time=datetime.datetime.now())
        self.scheduler.start()
