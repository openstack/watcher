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
import mock
import uuid

from apscheduler.schedulers import background

from watcher.decision_engine.audit import continuous
from watcher.decision_engine.audit import oneshot
from watcher.decision_engine.messaging import events
from watcher.metrics_engine.cluster_model_collector import manager
from watcher.objects import audit as audit_objects
from watcher.tests.db import base
from watcher.tests.decision_engine.strategy.strategies import \
    faker_cluster_state as faker
from watcher.tests.objects import utils as obj_utils


class TestOneShotAuditHandler(base.DbTestCase):
    def setUp(self):
        super(TestOneShotAuditHandler, self).setUp()
        obj_utils.create_test_goal(self.context, id=1, name="dummy")
        audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audit = obj_utils.create_test_audit(
            self.context,
            audit_template_id=audit_template.id)

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_without_errors(self, mock_collector):
        mock_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler(mock.MagicMock())
        audit_handler.execute(self.audit, self.context)

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_state_succeeded(self, mock_collector):
        mock_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler(mock.MagicMock())
        audit_handler.execute(self.audit, self.context)
        audit = audit_objects.Audit.get_by_uuid(self.context, self.audit.uuid)
        self.assertEqual(audit_objects.State.SUCCEEDED, audit.state)

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_send_notification(self, mock_collector):
        messaging = mock.MagicMock()
        mock_collector.return_value = faker.FakerModelCollector()
        audit_handler = oneshot.OneShotAuditHandler(messaging)
        audit_handler.execute(self.audit, self.context)

        call_on_going = mock.call(events.Events.TRIGGER_AUDIT.name, {
            'audit_status': audit_objects.State.ONGOING,
            'audit_uuid': self.audit.uuid})
        call_succeeded = mock.call(events.Events.TRIGGER_AUDIT.name, {
            'audit_status': audit_objects.State.SUCCEEDED,
            'audit_uuid': self.audit.uuid})

        calls = [call_on_going, call_succeeded]
        messaging.status_topic_handler.publish_event.assert_has_calls(calls)
        self.assertEqual(
            2, messaging.status_topic_handler.publish_event.call_count)


class TestContinuousAuditHandler(base.DbTestCase):
    def setUp(self):
        super(TestContinuousAuditHandler, self).setUp()
        obj_utils.create_test_goal(self.context, id=1, name="DUMMY")
        audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audits = [obj_utils.create_test_audit(
            self.context,
            uuid=uuid.uuid4(),
            audit_template_id=audit_template.id,
            audit_type=audit_objects.AuditType.CONTINUOUS.value)
            for i in range(2)]

    @mock.patch.object(background.BackgroundScheduler, 'add_job')
    @mock.patch.object(background.BackgroundScheduler, 'get_jobs')
    @mock.patch.object(audit_objects.Audit, 'list')
    def test_launch_audits_periodically(self, mock_list,
                                        mock_jobs, mock_add_job):
        audit_handler = continuous.ContinuousAuditHandler(mock.MagicMock())
        audits = [audit_objects.Audit.get_by_uuid(self.context,
                                                  self.audits[0].uuid)]
        mock_list.return_value = audits
        mock_jobs.return_value = mock.MagicMock()
        audit_handler.launch_audits_periodically()
        mock_add_job.assert_called()

    @mock.patch.object(background.BackgroundScheduler, 'add_job')
    @mock.patch.object(background.BackgroundScheduler, 'get_jobs')
    @mock.patch.object(audit_objects.Audit, 'list')
    def test_launch_multiply_audits_periodically(self, mock_list,
                                                 mock_jobs, mock_add_job):
        audit_handler = continuous.ContinuousAuditHandler(mock.MagicMock())
        audits = [audit_objects.Audit.get_by_uuid(
            self.context,
            audit.uuid) for audit in self.audits]
        mock_list.return_value = audits
        mock_jobs.return_value = mock.MagicMock()
        calls = [mock.call(audit_handler.execute_audit, 'interval',
                           args=[mock.ANY, mock.ANY],
                           seconds=3600,
                           name='execute_audit',
                           next_run_time=mock.ANY) for audit in self.audits]
        audit_handler.launch_audits_periodically()
        mock_add_job.assert_has_calls(calls)

    @mock.patch.object(background.BackgroundScheduler, 'add_job')
    @mock.patch.object(background.BackgroundScheduler, 'get_jobs')
    @mock.patch.object(audit_objects.Audit, 'list')
    def test_period_audit_not_called_when_deleted(self, mock_list,
                                                  mock_jobs, mock_add_job):
        audit_handler = continuous.ContinuousAuditHandler(mock.MagicMock())
        audits = [audit_objects.Audit.get_by_uuid(
            self.context,
            audit.uuid) for audit in self.audits]
        mock_list.return_value = audits
        mock_jobs.return_value = mock.MagicMock()
        audits[1].state = audit_objects.State.CANCELLED
        calls = [mock.call(audit_handler.execute_audit, 'interval',
                           args=[mock.ANY, mock.ANY],
                           seconds=3600,
                           name='execute_audit',
                           next_run_time=mock.ANY)]
        audit_handler.launch_audits_periodically()
        mock_add_job.assert_has_calls(calls)
