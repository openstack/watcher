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

from watcher.common import utils
from watcher.decision_engine.audit.default import DefaultAuditHandler
from watcher.decision_engine.messaging.audit_endpoint import AuditEndpoint
from watcher.metrics_engine.cluster_model_collector.manager import \
    CollectorManager
from watcher.tests.db.base import DbTestCase
from watcher.tests.decision_engine.strategy.strategies.faker_cluster_state \
    import FakerModelCollector
from watcher.tests.objects import utils as obj_utils


class TestAuditEndpoint(DbTestCase):
    def setUp(self):
        super(TestAuditEndpoint, self).setUp()
        self.audit_template = obj_utils.create_test_audit_template(
            self.context)
        self.audit = obj_utils.create_test_audit(
            self.context,
            audit_template_id=self.audit_template.id)

    @mock.patch.object(CollectorManager, "get_cluster_model_collector")
    def test_do_trigger_audit(self, mock_collector):
        mock_collector.return_value = FakerModelCollector()
        audit_uuid = utils.generate_uuid()

        audit_handler = DefaultAuditHandler(mock.MagicMock())
        endpoint = AuditEndpoint(audit_handler, max_workers=2)

        with mock.patch.object(DefaultAuditHandler, 'execute') as mock_call:
            mock_call.return_value = 0
            endpoint.do_trigger_audit(audit_handler, audit_uuid)

        mock_call.assert_called_once_with(audit_uuid, audit_handler)

    @mock.patch.object(CollectorManager, "get_cluster_model_collector")
    def test_trigger_audit(self, mock_collector):
        mock_collector.return_value = FakerModelCollector()
        audit_uuid = utils.generate_uuid()
        audit_handler = DefaultAuditHandler(mock.MagicMock())
        endpoint = AuditEndpoint(audit_handler, max_workers=2)

        with mock.patch.object(DefaultAuditHandler, 'execute') \
                as mock_call:
            mock_call.return_value = 0
            endpoint.trigger_audit(audit_handler, audit_uuid)

        mock_call.assert_called_once_with(audit_uuid, audit_handler)
