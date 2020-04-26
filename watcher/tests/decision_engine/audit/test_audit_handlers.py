# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
from unittest import mock

from oslo_config import cfg
from oslo_utils import uuidutils

from apscheduler import job

from watcher.applier import rpcapi
from watcher.common import exception
from watcher.common import scheduling
from watcher.db.sqlalchemy import api as sq_api
from watcher.decision_engine.audit import continuous
from watcher.decision_engine.audit import oneshot
from watcher.decision_engine.model.collector import manager
from watcher.decision_engine.strategy.strategies import base as base_strategy
from watcher.decision_engine.strategy.strategies import dummy_strategy
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.decision_engine.model import faker_cluster_state as faker
from watcher.tests.objects import utils as obj_utils


class TestOneShotAuditHandler(base.DbTestCase):

    def setUp(self):
        super(TestOneShotAuditHandler, self).setUp()
        p_audit_notifications = mock.patch.object(
            notifications, 'audit', autospec=True)
        self.m_audit_notifications = p_audit_notifications.start()
        self.addCleanup(p_audit_notifications.stop)

        self.goal = obj_utils.create_test_goal(
            self.context, id=1, name=dummy_strategy.DummyStrategy.get_name())
        self.strategy = obj_utils.create_test_strategy(
            self.context, name=dummy_strategy.DummyStrategy.get_name(),
            goal_id=self.goal.id)
        audit_template = obj_utils.create_test_audit_template(
            self.context, strategy_id=self.strategy.id)
        self.audit = obj_utils.create_test_audit(
            self.context,
            uuid=uuidutils.generate_uuid(),
            goal_id=self.goal.id,
            strategy_id=self.strategy.id,
            audit_template_id=audit_template.id,
            goal=self.goal)

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    @mock.patch.object(base_strategy.BaseStrategy, "compute_model",
                       mock.Mock(stale=False))
    def test_trigger_audit_without_errors(self, m_collector):
        m_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler()
        audit_handler.execute(self.audit, self.context)

        expected_calls = [
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.END),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.END)]

        self.assertEqual(
            expected_calls,
            self.m_audit_notifications.send_action_notification.call_args_list)

    @mock.patch.object(base_strategy.BaseStrategy, "do_execute")
    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_with_error(self, m_collector, m_do_execute):
        m_collector.return_value = faker.FakerModelCollector()
        m_do_execute.side_effect = Exception
        audit_handler = oneshot.OneShotAuditHandler()
        audit_handler.execute(self.audit, self.context)

        expected_calls = [
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      priority=objects.fields.NotificationPriority.ERROR,
                      phase=objects.fields.NotificationPhase.ERROR)]

        self.assertEqual(
            expected_calls,
            self.m_audit_notifications.send_action_notification.call_args_list)

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    @mock.patch.object(base_strategy.BaseStrategy, "compute_model",
                       mock.Mock(stale=False))
    def test_trigger_audit_state_succeeded(self, m_collector):
        m_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler()
        audit_handler.execute(self.audit, self.context)
        audit = objects.audit.Audit.get_by_uuid(self.context, self.audit.uuid)
        self.assertEqual(objects.audit.State.SUCCEEDED, audit.state)

        expected_calls = [
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.END),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.END)]

        self.assertEqual(
            expected_calls,
            self.m_audit_notifications.send_action_notification.call_args_list)

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    @mock.patch.object(base_strategy.BaseStrategy, "compute_model",
                       mock.Mock(stale=False))
    def test_trigger_audit_send_notification(self, m_collector):
        m_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler()
        audit_handler.execute(self.audit, self.context)

        expected_calls = [
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.END),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audit,
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.END)]

        self.assertEqual(
            expected_calls,
            self.m_audit_notifications.send_action_notification.call_args_list)


class TestAutoTriggerActionPlan(base.DbTestCase):

    def setUp(self):
        super(TestAutoTriggerActionPlan, self).setUp()
        self.goal = obj_utils.create_test_goal(
            self.context, id=1, name=dummy_strategy.DummyStrategy.get_name())
        self.strategy = obj_utils.create_test_strategy(
            self.context, name=dummy_strategy.DummyStrategy.get_name(),
            goal_id=self.goal.id)
        audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audit = obj_utils.create_test_audit(
            self.context,
            id=0,
            uuid=uuidutils.generate_uuid(),
            audit_template_id=audit_template.id,
            goal_id=self.goal.id,
            audit_type=objects.audit.AuditType.CONTINUOUS.value,
            goal=self.goal,
            auto_trigger=True)
        self.ongoing_action_plan = obj_utils.create_test_action_plan(
            self.context,
            uuid=uuidutils.generate_uuid(),
            audit_id=self.audit.id,
            strategy_id=self.strategy.id,
            audit=self.audit,
            strategy=self.strategy,
        )
        self.recommended_action_plan = obj_utils.create_test_action_plan(
            self.context,
            uuid=uuidutils.generate_uuid(),
            state=objects.action_plan.State.ONGOING,
            audit_id=self.audit.id,
            strategy_id=self.strategy.id,
            audit=self.audit,
            strategy=self.strategy,
        )

    @mock.patch.object(oneshot.OneShotAuditHandler, 'do_execute')
    @mock.patch.object(objects.action_plan.ActionPlan, 'list')
    def test_trigger_audit_with_actionplan_ongoing(self, mock_list,
                                                   mock_do_execute):
        mock_list.return_value = [self.ongoing_action_plan]
        audit_handler = oneshot.OneShotAuditHandler()
        audit_handler.execute(self.audit, self.context)
        self.assertFalse(mock_do_execute.called)

    @mock.patch.object(rpcapi.ApplierAPI, 'launch_action_plan')
    @mock.patch.object(objects.action_plan.ActionPlan, 'list')
    @mock.patch.object(objects.audit.Audit, 'get_by_id')
    def test_trigger_action_plan_without_ongoing(self, mock_get_by_id,
                                                 mock_list, mock_applier):
        mock_get_by_id.return_value = self.audit
        mock_list.return_value = []
        auto_trigger_handler = oneshot.OneShotAuditHandler()
        with mock.patch.object(auto_trigger_handler,
                               'do_schedule') as m_schedule:
            m_schedule().uuid = self.recommended_action_plan.uuid
            auto_trigger_handler.post_execute(self.audit, mock.MagicMock(),
                                              self.context)
        mock_applier.assert_called_once_with(self.context,
                                             self.recommended_action_plan.uuid)

    @mock.patch.object(oneshot.OneShotAuditHandler, 'do_execute')
    def test_trigger_audit_with_force(self, mock_do_execute):
        audit_handler = oneshot.OneShotAuditHandler()
        self.audit.force = True
        audit_handler.execute(self.audit, self.context)
        self.assertTrue(mock_do_execute.called)


class TestContinuousAuditHandler(base.DbTestCase):

    def setUp(self):
        super(TestContinuousAuditHandler, self).setUp()
        p_audit_notifications = mock.patch.object(
            notifications, 'audit', autospec=True)
        self.m_audit_notifications = p_audit_notifications.start()
        self.addCleanup(p_audit_notifications.stop)

        self.goal = obj_utils.create_test_goal(
            self.context, id=1, name=dummy_strategy.DummyStrategy.get_name())
        audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audits = [
            obj_utils.create_test_audit(
                self.context,
                id=id_,
                name='My Audit {0}'.format(id_),
                uuid=uuidutils.generate_uuid(),
                audit_template_id=audit_template.id,
                goal_id=self.goal.id,
                audit_type=objects.audit.AuditType.CONTINUOUS.value,
                goal=self.goal,
                hostname='hostname1')
            for id_ in range(2, 4)]
        cfg.CONF.set_override("host", "hostname1")

    @mock.patch.object(objects.service.Service, 'list')
    @mock.patch.object(sq_api, 'get_engine')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'add_job')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_launch_audits_periodically_with_interval(
            self, mock_list, mock_jobs, m_add_job, m_engine, m_service):
        audit_handler = continuous.ContinuousAuditHandler()
        mock_list.return_value = self.audits
        self.audits[0].next_run_time = (datetime.datetime.now() -
                                        datetime.timedelta(seconds=1800))
        mock_jobs.return_value = mock.MagicMock()
        m_engine.return_value = mock.MagicMock()
        m_add_job.return_value = mock.MagicMock()

        audit_handler.launch_audits_periodically()
        m_service.assert_called()
        m_engine.assert_called()
        m_add_job.assert_called()
        mock_jobs.assert_called()
        self.assertIsNotNone(self.audits[0].next_run_time)
        self.assertIsNone(self.audits[1].next_run_time)

    @mock.patch.object(objects.service.Service, 'list')
    @mock.patch.object(sq_api, 'get_engine')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'add_job')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_launch_audits_periodically_with_cron(
            self, mock_list, mock_jobs, m_add_job, m_engine, m_service):
        audit_handler = continuous.ContinuousAuditHandler()
        mock_list.return_value = self.audits
        self.audits[0].interval = "*/5 * * * *"
        mock_jobs.return_value = mock.MagicMock()
        m_engine.return_value = mock.MagicMock()
        m_add_job.return_value = mock.MagicMock()

        audit_handler.launch_audits_periodically()
        m_service.assert_called()
        m_engine.assert_called()
        m_add_job.assert_called()
        mock_jobs.assert_called()
        self.assertIsNotNone(self.audits[0].next_run_time)
        self.assertIsNone(self.audits[1].next_run_time)

    @mock.patch.object(continuous.ContinuousAuditHandler, '_next_cron_time')
    @mock.patch.object(objects.service.Service, 'list')
    @mock.patch.object(sq_api, 'get_engine')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'add_job')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_launch_audits_periodically_with_invalid_cron(
            self, mock_list, mock_jobs, m_add_job, m_engine, m_service,
            mock_cron):
        audit_handler = continuous.ContinuousAuditHandler()
        mock_list.return_value = self.audits
        self.audits[0].interval = "*/5* * * *"
        mock_cron.side_effect = exception.CronFormatIsInvalid
        mock_jobs.return_value = mock.MagicMock()
        m_engine.return_value = mock.MagicMock()
        m_add_job.return_value = mock.MagicMock()

        self.assertRaises(exception.CronFormatIsInvalid,
                          audit_handler.launch_audits_periodically)

    @mock.patch.object(objects.service.Service, 'list')
    @mock.patch.object(sq_api, 'get_engine')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'add_job')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_launch_multiply_audits_periodically(self, mock_list,
                                                 mock_jobs, m_add_job,
                                                 m_engine, m_service):
        audit_handler = continuous.ContinuousAuditHandler()
        mock_list.return_value = self.audits
        mock_jobs.return_value = mock.MagicMock()
        m_engine.return_value = mock.MagicMock()
        m_service.return_value = mock.MagicMock()
        calls = [mock.call(audit_handler.execute_audit, 'interval',
                           args=[mock.ANY, mock.ANY],
                           seconds=3600,
                           name='execute_audit',
                           next_run_time=mock.ANY) for _ in self.audits]
        audit_handler.launch_audits_periodically()
        m_add_job.assert_has_calls(calls)

    @mock.patch.object(objects.service.Service, 'list')
    @mock.patch.object(sq_api, 'get_engine')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'add_job')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_period_audit_not_called_when_deleted(self, mock_list,
                                                  mock_jobs, m_add_job,
                                                  m_engine, m_service):
        audit_handler = continuous.ContinuousAuditHandler()
        mock_list.return_value = self.audits
        mock_jobs.return_value = mock.MagicMock()
        m_service.return_value = mock.MagicMock()
        m_engine.return_value = mock.MagicMock()

        ap_jobs = [job.Job(mock.MagicMock(), name='execute_audit',
                           func=audit_handler.execute_audit,
                           args=(self.audits[0], mock.MagicMock()),
                           kwargs={}),
                   job.Job(mock.MagicMock(), name='execute_audit',
                           func=audit_handler.execute_audit,
                           args=(self.audits[1], mock.MagicMock()),
                           kwargs={})
                   ]
        mock_jobs.return_value = ap_jobs
        audit_handler.launch_audits_periodically()

        audit_handler.update_audit_state(self.audits[1],
                                         objects.audit.State.CANCELLED)
        audit_handler.update_audit_state(self.audits[0],
                                         objects.audit.State.SUSPENDED)
        is_inactive = audit_handler._is_audit_inactive(self.audits[1])
        self.assertTrue(is_inactive)
        is_inactive = audit_handler._is_audit_inactive(self.audits[0])
        self.assertTrue(is_inactive)

    @mock.patch.object(objects.service.Service, 'list')
    @mock.patch.object(sq_api, 'get_engine')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    @mock.patch.object(objects.audit.AuditStateTransitionManager,
                       'is_inactive')
    @mock.patch.object(continuous.ContinuousAuditHandler, 'execute')
    def test_execute_audit_with_interval_no_job(
            self,
            m_execute,
            m_is_inactive,
            m_get_jobs,
            m_get_engine,
            m_service):
        audit_handler = continuous.ContinuousAuditHandler()
        self.audits[0].next_run_time = (datetime.datetime.now() -
                                        datetime.timedelta(seconds=1800))
        m_is_inactive.return_value = True
        m_get_jobs.return_value = []

        audit_handler.execute_audit(self.audits[0], self.context)
        self.assertIsNotNone(self.audits[0].next_run_time)

    @mock.patch.object(objects.service.Service, 'list')
    @mock.patch.object(sq_api, 'get_engine')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'remove_job')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'add_job')
    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_launch_audits_periodically_with_diff_interval(
            self, mock_list, mock_jobs, m_add_job, m_remove_job,
            m_engine, m_service):
        audit_handler = continuous.ContinuousAuditHandler()
        mock_list.return_value = self.audits
        self.audits[0].next_run_time = (datetime.datetime.now() -
                                        datetime.timedelta(seconds=1800))
        m_job1 = mock.MagicMock()
        m_job1.name = 'execute_audit'
        m_audit = mock.MagicMock()
        m_audit.uuid = self.audits[0].uuid
        m_audit.interval = 60
        m_job1.args = [m_audit]
        mock_jobs.return_value = [m_job1]
        m_engine.return_value = mock.MagicMock()
        m_add_job.return_value = mock.MagicMock()

        audit_handler.launch_audits_periodically()
        m_service.assert_called()
        m_engine.assert_called()
        m_add_job.assert_called()
        mock_jobs.assert_called()
        self.assertIsNotNone(self.audits[0].next_run_time)
        self.assertIsNone(self.audits[1].next_run_time)

        audit_handler.launch_audits_periodically()
        m_remove_job.assert_called()

    @mock.patch.object(continuous.ContinuousAuditHandler, 'get_planner',
                       mock.Mock())
    @mock.patch.object(base_strategy.BaseStrategy, "compute_model",
                       mock.Mock(stale=False))
    def test_execute_audit(self):
        audit_handler = continuous.ContinuousAuditHandler()
        audit_handler.execute_audit(self.audits[0], self.context)

        expected_calls = [
            mock.call(self.context, self.audits[0],
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audits[0],
                      action=objects.fields.NotificationAction.STRATEGY,
                      phase=objects.fields.NotificationPhase.END),
            mock.call(self.context, self.audits[0],
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.audits[0],
                      action=objects.fields.NotificationAction.PLANNER,
                      phase=objects.fields.NotificationPhase.END)]

        self.assertEqual(
            expected_calls,
            self.m_audit_notifications.send_action_notification.call_args_list)

    @mock.patch.object(scheduling.BackgroundSchedulerService, 'get_jobs')
    def test_is_audit_inactive(self, mock_jobs):
        audit_handler = continuous.ContinuousAuditHandler()
        mock_jobs.return_value = mock.MagicMock()
        audit_handler._audit_scheduler = mock.MagicMock()

        ap_jobs = [job.Job(mock.MagicMock(), name='execute_audit',
                           func=audit_handler.execute_audit,
                           args=(self.audits[0], mock.MagicMock()),
                           kwargs={}),
                   ]

        audit_handler.update_audit_state(self.audits[1],
                                         objects.audit.State.CANCELLED)
        mock_jobs.return_value = ap_jobs
        is_inactive = audit_handler._is_audit_inactive(self.audits[1])
        self.assertTrue(is_inactive)
        is_inactive = audit_handler._is_audit_inactive(self.audits[0])
        self.assertFalse(is_inactive)

    def test_check_audit_expired(self):
        current = datetime.datetime.utcnow()

        # start_time and end_time are None
        audit_handler = continuous.ContinuousAuditHandler()
        result = audit_handler.check_audit_expired(self.audits[0])
        self.assertFalse(result)
        self.assertIsNone(self.audits[0].start_time)
        self.assertIsNone(self.audits[0].end_time)

        # current time < start_time and end_time is None
        self.audits[0].start_time = current+datetime.timedelta(days=1)
        result = audit_handler.check_audit_expired(self.audits[0])
        self.assertTrue(result)
        self.assertIsNone(self.audits[0].end_time)

        # current time is between start_time and end_time
        self.audits[0].start_time = current-datetime.timedelta(days=1)
        self.audits[0].end_time = current+datetime.timedelta(days=1)
        result = audit_handler.check_audit_expired(self.audits[0])
        self.assertFalse(result)

        # current time > end_time
        self.audits[0].end_time = current-datetime.timedelta(days=1)
        result = audit_handler.check_audit_expired(self.audits[0])
        self.assertTrue(result)
        self.assertEqual(objects.audit.State.SUCCEEDED, self.audits[0].state)
