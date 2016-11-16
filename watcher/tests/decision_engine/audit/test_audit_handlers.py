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

from apscheduler.schedulers import background
import mock
from oslo_utils import uuidutils

from watcher.decision_engine.audit import continuous
from watcher.decision_engine.audit import oneshot
from watcher.decision_engine.model.collector import manager
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
    def test_trigger_audit_without_errors(self, m_collector):
        m_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler(mock.MagicMock())
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

    @mock.patch.object(dummy_strategy.DummyStrategy, "do_execute")
    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_with_error(self, m_collector, m_do_execute):
        m_collector.return_value = faker.FakerModelCollector()
        m_do_execute.side_effect = Exception
        audit_handler = oneshot.OneShotAuditHandler(mock.MagicMock())
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
    def test_trigger_audit_state_succeeded(self, m_collector):
        m_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler(mock.MagicMock())
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
    def test_trigger_audit_send_notification(self, m_collector):
        messaging = mock.MagicMock()
        m_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler(messaging)
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


class TestContinuousAuditHandler(base.DbTestCase):

    def setUp(self):
        super(TestContinuousAuditHandler, self).setUp()
        self.goal = obj_utils.create_test_goal(
            self.context, id=1, name=dummy_strategy.DummyStrategy.get_name())
        audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audits = [
            obj_utils.create_test_audit(
                self.context,
                id=id_,
                uuid=uuidutils.generate_uuid(),
                audit_template_id=audit_template.id,
                goal_id=self.goal.id,
                audit_type=objects.audit.AuditType.CONTINUOUS.value,
                goal=self.goal)
            for id_ in range(2, 4)]

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    @mock.patch.object(background.BackgroundScheduler, 'add_job')
    @mock.patch.object(background.BackgroundScheduler, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_launch_audits_periodically(self, mock_list, mock_jobs,
                                        m_add_job, m_collector):
        audit_handler = continuous.ContinuousAuditHandler(mock.MagicMock())
        mock_list.return_value = self.audits
        mock_jobs.return_value = mock.MagicMock()
        m_add_job.return_value = audit_handler.execute_audit(
            self.audits[0], self.context)
        m_collector.return_value = faker.FakerModelCollector()

        audit_handler.launch_audits_periodically()
        m_add_job.assert_called()

    @mock.patch.object(background.BackgroundScheduler, 'add_job')
    @mock.patch.object(background.BackgroundScheduler, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_launch_multiply_audits_periodically(self, mock_list,
                                                 mock_jobs, m_add_job):
        audit_handler = continuous.ContinuousAuditHandler(mock.MagicMock())
        mock_list.return_value = self.audits
        mock_jobs.return_value = mock.MagicMock()
        calls = [mock.call(audit_handler.execute_audit, 'interval',
                           args=[mock.ANY, mock.ANY],
                           seconds=3600,
                           name='execute_audit',
                           next_run_time=mock.ANY) for audit in self.audits]
        audit_handler.launch_audits_periodically()
        m_add_job.assert_has_calls(calls)

    @mock.patch.object(background.BackgroundScheduler, 'add_job')
    @mock.patch.object(background.BackgroundScheduler, 'get_jobs')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_period_audit_not_called_when_deleted(self, mock_list,
                                                  mock_jobs, m_add_job):
        audit_handler = continuous.ContinuousAuditHandler(mock.MagicMock())
        mock_list.return_value = self.audits
        mock_jobs.return_value = mock.MagicMock()
        self.audits[1].state = objects.audit.State.CANCELLED
        calls = [mock.call(audit_handler.execute_audit, 'interval',
                           args=[mock.ANY, mock.ANY],
                           seconds=3600,
                           name='execute_audit',
                           next_run_time=mock.ANY)]
        audit_handler.launch_audits_periodically()
        m_add_job.assert_has_calls(calls)

        audit_handler.update_audit_state(self.audits[1],
                                         objects.audit.State.CANCELLED)
        is_inactive = audit_handler._is_audit_inactive(self.audits[1])
        self.assertTrue(is_inactive)
