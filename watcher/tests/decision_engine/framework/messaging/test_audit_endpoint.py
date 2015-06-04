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
"""
import mock
from mock import MagicMock
from watcher.common import utils
from watcher.decision_engine.framework.command.trigger_audit_command import \
    TriggerAuditCommand
from watcher.decision_engine.framework.messaging.audit_endpoint import \
    AuditEndpoint
from watcher.tests import base


class TestAuditEndpoint(base.TestCase):

    def setUp(self):
        super(TestAuditEndpoint, self).setUp()
        self.endpoint = AuditEndpoint(MagicMock())

    def test_trigger_audit(self):
        audit_uuid = utils.generate_uuid()
        # todo() add

        with mock.patch.object(TriggerAuditCommand, 'execute') as mock_call:
            expected_uuid = self.endpoint.trigger_audit(
                self.context, audit_uuid)
            self.assertEqual(audit_uuid, expected_uuid)
            mock_call.assert_called_once_with(audit_uuid, self.context)
"""
