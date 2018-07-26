# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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
from apscheduler.triggers import interval as interval_trigger
import eventlet
import mock

from oslo_config import cfg
from oslo_utils import uuidutils

from watcher.decision_engine.loading import default as default_loading
from watcher.decision_engine import scheduling
from watcher.decision_engine.strategy.strategies import dummy_strategy
from watcher import notifications
from watcher import objects
from watcher.tests import base
from watcher.tests.db import base as db_base
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.objects import utils as obj_utils


class TestCancelOngoingAudits(db_base.DbTestCase):

    def setUp(self):
        super(TestCancelOngoingAudits, self).setUp()
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
            id=999,
            name='My Audit 999',
            uuid=uuidutils.generate_uuid(),
            audit_template_id=audit_template.id,
            goal_id=self.goal.id,
            audit_type=objects.audit.AuditType.ONESHOT.value,
            goal=self.goal,
            hostname='hostname1',
            state=objects.audit.State.ONGOING)
        cfg.CONF.set_override("host", "hostname1")

    @mock.patch.object(objects.audit.Audit, 'save')
    @mock.patch.object(objects.audit.Audit, 'list')
    def test_cancel_ongoing_audits(self, m_list, m_save):
        m_list.return_value = [self.audit]
        scheduler = scheduling.DecisionEngineSchedulingService()

        scheduler.cancel_ongoing_audits()
        m_list.assert_called()
        m_save.assert_called()
        self.assertEqual(self.audit.state, objects.audit.State.CANCELLED)


@mock.patch.object(objects.audit.Audit, 'save')
@mock.patch.object(objects.audit.Audit, 'list')
class TestDecisionEngineSchedulingService(base.TestCase):

    @mock.patch.object(
        default_loading.ClusterDataModelCollectorLoader, 'load')
    @mock.patch.object(
        default_loading.ClusterDataModelCollectorLoader, 'list_available')
    @mock.patch.object(background.BackgroundScheduler, 'start')
    def test_start_de_scheduling_service(self, m_start, m_list_available,
                                         m_load, m_list, m_save):
        m_list_available.return_value = {
            'fake': faker_cluster_state.FakerModelCollector}
        fake_collector = faker_cluster_state.FakerModelCollector(
            config=mock.Mock(period=777))
        m_load.return_value = fake_collector

        scheduler = scheduling.DecisionEngineSchedulingService()

        scheduler.start()

        m_start.assert_called_once_with(scheduler)
        jobs = scheduler.get_jobs()
        self.assertEqual(2, len(jobs))

        job = jobs[0]
        self.assertTrue(bool(fake_collector.cluster_data_model))

        self.assertIsInstance(job.trigger, interval_trigger.IntervalTrigger)

    @mock.patch.object(
        default_loading.ClusterDataModelCollectorLoader, 'load')
    @mock.patch.object(
        default_loading.ClusterDataModelCollectorLoader, 'list_available')
    @mock.patch.object(background.BackgroundScheduler, 'start')
    def test_execute_sync_job_fails(self, m_start, m_list_available,
                                    m_load, m_list, m_save):
        fake_config = mock.Mock(period=.01)
        fake_collector = faker_cluster_state.FakerModelCollector(
            config=fake_config)
        fake_collector.synchronize = mock.Mock(
            side_effect=lambda: eventlet.sleep(.5))
        m_list_available.return_value = {
            'fake': faker_cluster_state.FakerModelCollector}
        m_load.return_value = fake_collector

        scheduler = scheduling.DecisionEngineSchedulingService()

        scheduler.start()

        m_start.assert_called_once_with(scheduler)
        jobs = scheduler.get_jobs()
        self.assertEqual(2, len(jobs))

        job = jobs[0]
        job.func()
        self.assertFalse(bool(fake_collector.cluster_data_model))

        self.assertIsInstance(job.trigger, interval_trigger.IntervalTrigger)
