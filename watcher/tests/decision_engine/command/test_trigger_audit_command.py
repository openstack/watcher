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

from mock import call
from mock import MagicMock
from watcher.decision_engine.command.audit import TriggerAuditCommand
from watcher.decision_engine.messaging.events import Events
from watcher.objects.audit import Audit
from watcher.objects.audit import AuditStatus
from watcher.tests.db.base import DbTestCase
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerModelCollector
from watcher.tests.objects import utils as obj_utils


class TestTriggerAuditCommand(DbTestCase):
    def setUp(self):
        super(TestTriggerAuditCommand, self).setUp()
        self.audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audit = obj_utils.create_test_audit(
            self.context,
            audit_template_id=self.audit_template.id)

    def test_trigger_audit_without_errors(self):
        model_collector = FakerModelCollector()
        command = TriggerAuditCommand(MagicMock(), model_collector)
        command.execute(self.audit.uuid, self.context)

    def test_trigger_audit_state_success(self):
        model_collector = FakerModelCollector()
        command = TriggerAuditCommand(MagicMock(), model_collector)
        command.strategy_context.execute_strategy = MagicMock()
        command.execute(self.audit.uuid, self.context)
        audit = Audit.get_by_uuid(self.context, self.audit.uuid)
        self.assertEqual(AuditStatus.SUCCEEDED, audit.state)

    def test_trigger_audit_send_notification(self):
        messaging = MagicMock()
        model_collector = FakerModelCollector()
        command = TriggerAuditCommand(messaging, model_collector)
        command.strategy_context.execute_strategy = MagicMock()

        command.execute(self.audit.uuid, self.context)

        call_on_going = call(Events.TRIGGER_AUDIT.name, {
            'audit_status': AuditStatus.ONGOING,
            'audit_uuid': self.audit.uuid})
        call_succeeded = call(Events.TRIGGER_AUDIT.name, {
            'audit_status': AuditStatus.SUCCEEDED,
            'audit_uuid': self.audit.uuid})

        calls = [call_on_going, call_succeeded]
        messaging.topic_status.publish_event.assert_has_calls(calls)
        self.assertEqual(2, messaging.topic_status.publish_event.call_count)
