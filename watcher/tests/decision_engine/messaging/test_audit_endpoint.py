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

from unittest import mock

from watcher.decision_engine.audit import continuous as continuous_handler
from watcher.decision_engine.audit import oneshot as oneshot_handler
from watcher.decision_engine.messaging import audit_endpoint
from watcher.decision_engine.model.collector import manager
from watcher.tests.db import base
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.objects import utils as obj_utils


class TestAuditEndpoint(base.DbTestCase):
    def setUp(self):
        super(TestAuditEndpoint, self).setUp()
        self.goal = obj_utils.create_test_goal(self.context)
        self.audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audit = obj_utils.create_test_audit(
            self.context,
            audit_template_id=self.audit_template.id)

    @mock.patch.object(continuous_handler.ContinuousAuditHandler, 'start')
    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    def test_do_trigger_audit(self, mock_collector, mock_handler):
        mock_collector.return_value = faker_cluster_state.FakerModelCollector()

        audit_handler = oneshot_handler.OneShotAuditHandler
        endpoint = audit_endpoint.AuditEndpoint(audit_handler)

        with mock.patch.object(oneshot_handler.OneShotAuditHandler,
                               'execute') as mock_call:
            mock_call.return_value = 0
            endpoint.do_trigger_audit(self.context, self.audit.uuid)

        self.assertEqual(mock_call.call_count, 1)

    @mock.patch.object(continuous_handler.ContinuousAuditHandler, 'start')
    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit(self, mock_collector, mock_handler):
        mock_collector.return_value = faker_cluster_state.FakerModelCollector()

        audit_handler = oneshot_handler.OneShotAuditHandler
        endpoint = audit_endpoint.AuditEndpoint(audit_handler)

        with mock.patch.object(endpoint.executor, 'submit') as mock_call:
            mock_execute = mock.call(endpoint.do_trigger_audit,
                                     self.context,
                                     self.audit.uuid)
            endpoint.trigger_audit(self.context, self.audit.uuid)

        mock_call.assert_has_calls([mock_execute])
        self.assertEqual(mock_call.call_count, 1)
