# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from unittest import mock

from watcher.decision_engine import rpcapi as deapi
from watcher import objects
from watcher.tests.api import base as api_base
from watcher.tests.objects import utils as obj_utils


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit_template(self.context)

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_trigger_audit(self, mock_trigger_audit):
        audit = obj_utils.create_test_audit(
            self.context,
            audit_type=objects.audit.AuditType.EVENT.value)
        response = self.post_json(
            '/webhooks/%s' % audit['uuid'], {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'})
        self.assertEqual(202, response.status_int)
        mock_trigger_audit.assert_called_once_with(
            mock.ANY, audit['uuid'])

    def test_trigger_audit_with_no_audit(self):
        response = self.post_json(
            '/webhooks/no-audit', {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_trigger_audit_with_not_allowed_audittype(self):
        audit = obj_utils.create_test_audit(self.context)
        response = self.post_json(
            '/webhooks/%s' % audit['uuid'], {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_trigger_audit_with_not_allowed_audit_state(self):
        audit = obj_utils.create_test_audit(
            self.context,
            audit_type=objects.audit.AuditType.EVENT.value,
            state=objects.audit.State.FAILED)
        response = self.post_json(
            '/webhooks/%s' % audit['uuid'], {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
