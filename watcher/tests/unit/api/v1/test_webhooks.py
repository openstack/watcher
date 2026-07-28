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

from http import HTTPStatus

import ddt

from oslo_config import cfg

from watcher.common import context as watcher_context
from watcher.decision_engine import rpcapi as deapi
from watcher import objects
from watcher.tests.unit.api import base as api_base
from watcher.tests.unit.objects import utils as obj_utils


CONF = cfg.CONF


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super().setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit_template(self.context)

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_trigger_audit(self, mock_trigger_audit):
        audit = obj_utils.create_test_audit(
            self.context,
            audit_type=objects.audit.AuditType.EVENT.value)
        response = self.post_json(
            '/webhooks/{}'.format(audit['uuid']), {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'})
        self.assertEqual(HTTPStatus.ACCEPTED, response.status_int)
        mock_trigger_audit.assert_called_once_with(
            mock.ANY, audit['uuid'])

    def test_trigger_audit_with_no_audit(self):
        response = self.post_json(
            '/webhooks/no-audit', {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_trigger_audit_with_not_allowed_audittype(self):
        audit = obj_utils.create_test_audit(self.context)
        response = self.post_json(
            '/webhooks/{}'.format(audit['uuid']), {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_trigger_audit_with_not_allowed_audit_state(self):
        audit = obj_utils.create_test_audit(
            self.context,
            audit_type=objects.audit.AuditType.EVENT.value,
            state=objects.audit.State.FAILED)
        response = self.post_json(
            '/webhooks/{}'.format(audit['uuid']), {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


@ddt.ddt
class TestWebhookPolicyEnforcement(api_base.FunctionalTest):
    def setUp(self):
        super().setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit_template(self.context)

    def _create_event_audit(self):
        return obj_utils.create_test_audit(
            self.context, audit_type=objects.audit.AuditType.EVENT.value
        )

    def _set_admin_or_service_policy(self):
        self.policy.set_rules(
            {
                'admin_or_service_api': (
                    'role:admin or role:administrator or role:service'
                ),
                'webhook:trigger': 'rule:admin_or_service_api',
            }
        )

    def _make_context_with_roles(self, roles):
        def make_context(*args, **kwargs):
            kwargs.setdefault('project_id', 'fake_project')
            kwargs.setdefault('user_id', 'fake_user')
            kwargs['roles'] = roles
            context = watcher_context.RequestContext(*args, **kwargs)
            return watcher_context.RequestContext.from_dict(context.to_dict())

        return make_context

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_trigger_policy_disallowed_without_admin_or_service_role(
        self, mock_trigger_audit
    ):
        CONF.set_override('enable_webhooks_auth', True, group='api')
        self._set_admin_or_service_policy()
        audit = self._create_event_audit()
        response = self.post_json(
            '/webhooks/{}'.format(audit['uuid']),
            {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True,
        )
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_int)
        mock_trigger_audit.assert_not_called()

    @mock.patch.object(watcher_context, 'make_context')
    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    @ddt.data("admin", "service")
    def test_trigger_policy_allowed_with_role(
        self, role, mock_trigger_audit, mock_make_context
    ):
        CONF.set_override('enable_webhooks_auth', True, group='api')
        self._set_admin_or_service_policy()
        mock_make_context.side_effect = self._make_context_with_roles([role])
        audit = self._create_event_audit()
        response = self.post_json(
            '/webhooks/{}'.format(audit['uuid']),
            {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
        )
        self.assertEqual(HTTPStatus.ACCEPTED, response.status_int)
        mock_trigger_audit.assert_called_once_with(mock.ANY, audit['uuid'])

    @mock.patch.object(watcher_context, 'make_context')
    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    @ddt.data("member", "reader")
    def test_trigger_policy_disallowed_with_role(
        self, role, mock_trigger_audit, mock_make_context
    ):
        CONF.set_override('enable_webhooks_auth', True, group='api')
        self._set_admin_or_service_policy()
        mock_make_context.side_effect = self._make_context_with_roles([role])
        audit = self._create_event_audit()
        response = self.post_json(
            '/webhooks/{}'.format(audit['uuid']),
            {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True,
        )
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_int)
        mock_trigger_audit.assert_not_called()

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_trigger_policy_not_enforced_when_auth_disabled(
        self, mock_trigger_audit
    ):
        CONF.set_override('enable_webhooks_auth', False, group='api')
        self._set_admin_or_service_policy()
        audit = self._create_event_audit()
        response = self.post_json(
            '/webhooks/{}'.format(audit['uuid']),
            {},
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
        )
        self.assertEqual(HTTPStatus.ACCEPTED, response.status_int)
        mock_trigger_audit.assert_called_once_with(mock.ANY, audit['uuid'])
