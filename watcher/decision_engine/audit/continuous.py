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
from dateutil import tz

from croniter import croniter

from watcher.common import context
from watcher.common import scheduling
from watcher.common import utils
from watcher import conf
from watcher.db.sqlalchemy import api as sq_api
from watcher.db.sqlalchemy import job_store
from watcher.decision_engine.audit import base
from watcher import objects


CONF = conf.CONF


class ContinuousAuditHandler(base.AuditHandler):
    def __init__(self):
        super(ContinuousAuditHandler, self).__init__()
        # scheduler for executing audits
        self._audit_scheduler = None
        # scheduler for a periodic task to launch audit
        self._period_scheduler = None
        self.context_show_deleted = context.RequestContext(is_admin=True,
                                                           show_deleted=True)

    @property
    def scheduler(self):
        if self._audit_scheduler is None:
            self._audit_scheduler = scheduling.BackgroundSchedulerService(
                jobstores={
                    'default': job_store.WatcherJobStore(
                        engine=sq_api.get_engine()),
                }
            )
        return self._audit_scheduler

    @property
    def period_scheduler(self):
        if self._period_scheduler is None:
            self._period_scheduler = scheduling.BackgroundSchedulerService()
        return self._period_scheduler

    def _is_audit_inactive(self, audit):
        audit = objects.Audit.get_by_uuid(
            self.context_show_deleted, audit.uuid, eager=True)
        if (objects.audit.AuditStateTransitionManager().is_inactive(audit) or
                (audit.hostname != CONF.host) or
                (self.check_audit_expired(audit))):
            # if audit isn't in active states, audit's job must be removed to
            # prevent using of inactive audit in future.
            jobs = [job for job in self.scheduler.get_jobs()
                    if job.name == 'execute_audit' and
                    job.args[0].uuid == audit.uuid]
            if jobs:
                jobs[0].remove()
            return True

        return False

    def do_execute(self, audit, request_context):
        solution = super(ContinuousAuditHandler, self)\
            .do_execute(audit, request_context)

        if audit.audit_type == objects.audit.AuditType.CONTINUOUS.value:
            a_plan_filters = {'audit_uuid': audit.uuid,
                              'state': objects.action_plan.State.RECOMMENDED}
            action_plans = objects.ActionPlan.list(
                request_context, filters=a_plan_filters, eager=True)
            for plan in action_plans:
                plan.state = objects.action_plan.State.CANCELLED
                plan.save()
        return solution

    @staticmethod
    def _next_cron_time(audit):
        if utils.is_cron_like(audit.interval):
            return croniter(audit.interval, datetime.datetime.utcnow()
                            ).get_next(datetime.datetime)

    @classmethod
    def execute_audit(cls, audit, request_context):
        self = cls()
        if not self._is_audit_inactive(audit):
            try:
                self.execute(audit, request_context)
            except Exception:
                raise
            finally:
                if utils.is_int_like(audit.interval):
                    audit.next_run_time = (
                        datetime.datetime.utcnow() +
                        datetime.timedelta(seconds=int(audit.interval)))
                else:
                    audit.next_run_time = self._next_cron_time(audit)
                audit.save()

    def _add_job(self, trigger, audit, audit_context, **trigger_args):
        time_var = 'next_run_time' if trigger_args.get(
            'next_run_time') else 'run_date'
        # We should convert UTC time to local time without tzinfo
        trigger_args[time_var] = trigger_args[time_var].replace(
            tzinfo=tz.tzutc()).astimezone(tz.tzlocal()).replace(tzinfo=None)
        self.scheduler.add_job(self.execute_audit, trigger,
                               args=[audit, audit_context],
                               name='execute_audit',
                               **trigger_args)

    def check_audit_expired(self, audit):
        current = datetime.datetime.utcnow()
        # Note: if audit still didn't get into the timeframe,
        #       skip it
        if audit.start_time and audit.start_time > current:
            return True
        if audit.end_time and audit.end_time < current:
            if audit.state != objects.audit.State.SUCCEEDED:
                audit.state = objects.audit.State.SUCCEEDED
                audit.save()
            return True

        return False

    def launch_audits_periodically(self):
        # if audit scheduler stop, restart it
        if not self.scheduler.running:
            self.scheduler.start()

        audit_context = context.RequestContext(is_admin=True)
        audit_filters = {
            'audit_type': objects.audit.AuditType.CONTINUOUS.value,
            'state__in': (objects.audit.State.PENDING,
                          objects.audit.State.ONGOING),
        }
        audit_filters['hostname'] = None
        unscheduled_audits = objects.Audit.list(
            audit_context, filters=audit_filters, eager=True)
        for audit in unscheduled_audits:
            # If continuous audit doesn't have a hostname yet,
            # Watcher will set current CONF.host value.
            # TODO(alexchadin): Add scheduling of new continuous audits.
            audit.hostname = CONF.host
            audit.save()
        scheduler_job_args = [
            (job.args[0].uuid, job) for job
            in self.scheduler.get_jobs()
            if job.name == 'execute_audit']
        scheduler_jobs = dict(scheduler_job_args)
        # if audit isn't in active states, audit's job should be removed
        jobs_to_remove = []
        for job in scheduler_jobs.values():
            if self._is_audit_inactive(job.args[0]):
                jobs_to_remove.append(job.args[0].uuid)
        for audit_uuid in jobs_to_remove:
            scheduler_jobs.pop(audit_uuid)
        audit_filters['hostname'] = CONF.host
        audits = objects.Audit.list(
            audit_context, filters=audit_filters, eager=True)
        for audit in audits:
            if self.check_audit_expired(audit):
                continue
            existing_job = scheduler_jobs.get(audit.uuid, None)
            # if audit is not presented in scheduled audits yet,
            # just add a new audit job.
            # if audit is already in the job queue, and interval has changed,
            # we need to remove the old job and add a new one.
            if (existing_job is None) or (
                existing_job and
                    audit.interval != existing_job.args[0].interval):
                if existing_job:
                    self.scheduler.remove_job(existing_job.id)
                # if interval is provided with seconds
                if utils.is_int_like(audit.interval):
                    # if audit has already been provided and we need
                    # to restore it after shutdown
                    if audit.next_run_time is not None:
                        old_run_time = audit.next_run_time
                        current = datetime.datetime.utcnow()
                        if old_run_time < current:
                            delta = datetime.timedelta(
                                seconds=(int(audit.interval) - (
                                    current - old_run_time).seconds %
                                    int(audit.interval)))
                            audit.next_run_time = current + delta
                        next_run_time = audit.next_run_time
                    # if audit is new one
                    else:
                        next_run_time = datetime.datetime.utcnow()
                    self._add_job('interval', audit, audit_context,
                                  seconds=int(audit.interval),
                                  next_run_time=next_run_time)

                else:
                    audit.next_run_time = self._next_cron_time(audit)
                    self._add_job('date', audit, audit_context,
                                  run_date=audit.next_run_time)
                audit.hostname = CONF.host
                audit.save()

    def start(self):
        self.period_scheduler.add_job(
            self.launch_audits_periodically,
            'interval',
            seconds=CONF.watcher_decision_engine.continuous_audit_interval,
            next_run_time=datetime.datetime.now())
        self.period_scheduler.start()
        # audit scheduler start
        self.scheduler.start()
