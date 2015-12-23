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

from watcher.decision_engine.audit.default import DefaultAuditHandler
from watcher.decision_engine.messaging.events import Events
from watcher.metrics_engine.cluster_model_collector.manager import \
    CollectorManager
from watcher.objects.audit import Audit
from watcher.objects.audit import AuditStatus
from watcher.tests.db.base import DbTestCase
from watcher.tests.decision_engine.strategy.strategies.faker_cluster_state \
    import FakerModelCollector
from watcher.tests.objects import utils as obj_utils


class TestDefaultAuditHandler(DbTestCase):
    def setUp(self):
        super(TestDefaultAuditHandler, self).setUp()
        self.audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audit = obj_utils.create_test_audit(
            self.context,
            audit_template_id=self.audit_template.id)

    @mock.patch.object(CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_without_errors(self, mock_collector):
        mock_collector.return_value = FakerModelCollector()
        audit_handler = DefaultAuditHandler(mock.MagicMock())
        audit_handler.execute(self.audit.uuid, self.context)

    @mock.patch.object(CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_state_success(self, mock_collector):
        mock_collector.return_value = FakerModelCollector()
        audit_handler = DefaultAuditHandler(mock.MagicMock())
        audit_handler.execute(self.audit.uuid, self.context)
        audit = Audit.get_by_uuid(self.context, self.audit.uuid)
        self.assertEqual(AuditStatus.SUCCEEDED, audit.state)

    @mock.patch.object(CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit_send_notification(self, mock_collector):
        messaging = mock.MagicMock()
        mock_collector.return_value = FakerModelCollector()
        audit_handler = DefaultAuditHandler(messaging)
        audit_handler.execute(self.audit.uuid, self.context)

        call_on_going = mock.call(Events.TRIGGER_AUDIT.name, {
            'audit_status': AuditStatus.ONGOING,
            'audit_uuid': self.audit.uuid})
        call_succeeded = mock.call(Events.TRIGGER_AUDIT.name, {
            'audit_status': AuditStatus.SUCCEEDED,
            'audit_uuid': self.audit.uuid})

        calls = [call_on_going, call_succeeded]
        messaging.topic_status.publish_event.assert_has_calls(calls)
        self.assertEqual(2, messaging.topic_status.publish_event.call_count)
