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

import datetime
import itertools
from unittest import mock

from http import HTTPStatus
from oslo_config import cfg
from oslo_serialization import jsonutils

from watcher.applier import rpcapi as aapi
from watcher.common import utils
from watcher.db import api as db_api
from watcher import objects
from watcher.tests.api import base as api_base
from watcher.tests.objects import utils as obj_utils


class TestListActionPlan(api_base.FunctionalTest):

    def setUp(self):
        super(TestListActionPlan, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)

    def test_empty(self):
        response = self.get_json('/action_plans')
        self.assertEqual([], response['action_plans'])

    def _assert_action_plans_fields(self, action_plan):
        action_plan_fields = [
            'uuid', 'audit_uuid', 'strategy_uuid', 'strategy_name',
            'state', 'global_efficacy', 'efficacy_indicators']
        for field in action_plan_fields:
            self.assertIn(field, action_plan)

    def test_one(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        response = self.get_json('/action_plans')
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

    def test_one_soft_deleted(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        action_plan.soft_delete()
        response = self.get_json('/action_plans',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

        response = self.get_json('/action_plans')
        self.assertEqual([], response['action_plans'])

    def test_get_one_ok(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        obj_utils.create_test_efficacy_indicator(
            self.context, action_plan_id=action_plan['id'])
        response = self.get_json('/action_plans/%s' % action_plan['uuid'])
        self.assertEqual(action_plan.uuid, response['uuid'])
        self._assert_action_plans_fields(response)
        self.assertEqual(
            [{'description': 'Test indicator',
              'name': 'test_indicator',
              'value': 0.0,
              'unit': '%'}],
            response['efficacy_indicators'])

    def test_get_one_soft_deleted(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        action_plan.soft_delete()
        response = self.get_json('/action_plans/%s' % action_plan['uuid'],
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action_plan.uuid, response['uuid'])
        self._assert_action_plans_fields(response)

        response = self.get_json('/action_plans/%s' % action_plan['uuid'],
                                 expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)

    def test_detail(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        response = self.get_json('/action_plans/detail')
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

    def test_detail_soft_deleted(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        action_plan.soft_delete()
        response = self.get_json('/action_plans/detail',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

        response = self.get_json('/action_plans/detail')
        self.assertEqual([], response['action_plans'])

    def test_detail_against_single(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        response = self.get_json(
            '/action_plan/%s/detail' % action_plan['uuid'],
            expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)

    def test_many(self):
        action_plan_list = []
        for id_ in range(5):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan_list.append(action_plan.uuid)
        response = self.get_json('/action_plans')
        self.assertEqual(len(action_plan_list), len(response['action_plans']))
        uuids = [s['uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(action_plan_list), sorted(uuids))

    def test_many_with_soft_deleted_audit_uuid(self):
        action_plan_list = []
        audit1 = obj_utils.create_test_audit(
            self.context, id=2,
            uuid=utils.generate_uuid(), name='My Audit {0}'.format(2))
        audit2 = obj_utils.create_test_audit(
            self.context, id=3,
            uuid=utils.generate_uuid(), name='My Audit {0}'.format(3))

        for id_ in range(0, 2):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit1.id)
            action_plan_list.append(action_plan.uuid)

        for id_ in range(2, 4):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit2.id)
            action_plan_list.append(action_plan.uuid)

        new_state = objects.audit.State.CANCELLED
        self.patch_json(
            '/audits/%s' % audit1.uuid,
            [{'path': '/state', 'value': new_state,
             'op': 'replace'}])
        self.delete('/audits/%s' % audit1.uuid)

        response = self.get_json('/action_plans')

        self.assertEqual(len(action_plan_list), len(response['action_plans']))

        for id_ in range(0, 2):
            action_plan = response['action_plans'][id_]
            self.assertIsNone(action_plan['audit_uuid'])

        for id_ in range(2, 4):
            action_plan = response['action_plans'][id_]
            self.assertEqual(audit2.uuid, action_plan['audit_uuid'])

    def test_many_with_audit_uuid(self):
        action_plan_list = []
        audit = obj_utils.create_test_audit(
            self.context, id=2,
            uuid=utils.generate_uuid(), name='My Audit {0}'.format(2))
        for id_ in range(2, 5):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit.id)
            action_plan_list.append(action_plan.uuid)
        response = self.get_json('/action_plans')
        self.assertEqual(len(action_plan_list), len(response['action_plans']))
        for action in response['action_plans']:
            self.assertEqual(audit.uuid, action['audit_uuid'])

    def test_many_with_audit_uuid_filter(self):
        action_plan_list1 = []
        audit1 = obj_utils.create_test_audit(
            self.context, id=2,
            uuid=utils.generate_uuid(), name='My Audit {0}'.format(2))
        for id_ in range(2, 5):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit1.id)
            action_plan_list1.append(action_plan.uuid)

        audit2 = obj_utils.create_test_audit(
            self.context, id=3,
            uuid=utils.generate_uuid(), name='My Audit {0}'.format(3))
        action_plan_list2 = []
        for id_ in [5, 6, 7]:
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit2.id)
            action_plan_list2.append(action_plan.uuid)

        response = self.get_json('/action_plans?audit_uuid=%s' % audit2.uuid)
        self.assertEqual(len(action_plan_list2), len(response['action_plans']))
        for action in response['action_plans']:
            self.assertEqual(audit2.uuid, action['audit_uuid'])

    def test_many_without_soft_deleted(self):
        action_plan_list = []
        for id_ in [1, 2, 3]:
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan_list.append(action_plan.uuid)
        for id_ in [4, 5]:
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan.soft_delete()
        response = self.get_json('/action_plans')
        self.assertEqual(3, len(response['action_plans']))
        uuids = [s['uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(action_plan_list), sorted(uuids))

    def test_many_with_soft_deleted(self):
        action_plan_list = []
        for id_ in [1, 2, 3]:
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan_list.append(action_plan.uuid)
        for id_ in [4, 5]:
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan.soft_delete()
            action_plan_list.append(action_plan.uuid)
        response = self.get_json('/action_plans',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(5, len(response['action_plans']))
        uuids = [s['uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(action_plan_list), sorted(uuids))

    def test_many_with_sort_key_audit_uuid(self):
        audit_list = []
        for id_ in range(2, 5):
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
            obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit.id)
            audit_list.append(audit.uuid)

        response = self.get_json('/action_plans/?sort_key=audit_uuid')

        self.assertEqual(3, len(response['action_plans']))
        uuids = [s['audit_uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(audit_list), uuids)

    def test_sort_key_validation(self):
        response = self.get_json(
            '/action_plans?sort_key=%s' % 'bad_name',
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_action_plan(self.context, id=1, uuid=uuid)
        response = self.get_json('/action_plans/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for link in response['links']:
            bookmark = link['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(
                link['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
        response = self.get_json('/action_plans/?limit=3')
        self.assertEqual(3, len(response['action_plans']))

        next_marker = response['action_plans'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
        response = self.get_json('/action_plans')
        self.assertEqual(3, len(response['action_plans']))

        next_marker = response['action_plans'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(
            self.context)
        p = mock.patch.object(db_api.BaseConnection, 'destroy_action_plan')
        self.mock_action_plan_delete = p.start()
        self.mock_action_plan_delete.side_effect = \
            self._simulate_rpc_action_plan_delete
        self.addCleanup(p.stop)

    def _simulate_rpc_action_plan_delete(self, audit_uuid):
        action_plan = objects.ActionPlan.get_by_uuid(self.context, audit_uuid)
        action_plan.destroy()

    def test_delete_action_plan_without_action(self):
        response = self.delete('/action_plans/%s' % self.action_plan.uuid,
                               expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
        self.action_plan.state = objects.action_plan.State.SUCCEEDED
        self.action_plan.save()
        self.delete('/action_plans/%s' % self.action_plan.uuid)
        response = self.get_json('/action_plans/%s' % self.action_plan.uuid,
                                 expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_action_plan_with_action(self):
        action = obj_utils.create_test_action(
            self.context, id=1)

        self.action_plan.state = objects.action_plan.State.SUCCEEDED
        self.action_plan.save()
        self.delete('/action_plans/%s' % self.action_plan.uuid)
        ap_response = self.get_json('/action_plans/%s' % self.action_plan.uuid,
                                    expect_errors=True)
        acts_response = self.get_json(
            '/actions/?action_plan_uuid=%s' % self.action_plan.uuid)
        act_response = self.get_json(
            '/actions/%s' % action.uuid,
            expect_errors=True)

        # The action plan does not exist anymore
        self.assertEqual(HTTPStatus.NOT_FOUND, ap_response.status_int)
        self.assertEqual('application/json', ap_response.content_type)
        self.assertTrue(ap_response.json['error_message'])

        # Nor does the action
        self.assertEqual(0, len(acts_response['actions']))
        self.assertEqual(HTTPStatus.NOT_FOUND, act_response.status_int)
        self.assertEqual('application/json', act_response.content_type)
        self.assertTrue(act_response.json['error_message'])

    def test_delete_action_plan_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/action_plans/%s' % uuid, expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestStart(api_base.FunctionalTest):

    def setUp(self):
        super(TestStart, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(
            self.context, state=objects.action_plan.State.RECOMMENDED)
        p = mock.patch.object(db_api.BaseConnection, 'update_action_plan')
        self.mock_action_plan_update = p.start()
        self.mock_action_plan_update.side_effect = \
            self._simulate_rpc_action_plan_update
        self.addCleanup(p.stop)

    def _simulate_rpc_action_plan_update(self, action_plan):
        action_plan.save()
        return action_plan

    @mock.patch('watcher.common.policy.enforce')
    def test_start_action_plan_not_found(self, mock_policy):
        mock_policy.return_value = True
        uuid = utils.generate_uuid()
        response = self.post('/v1/action_plans/%s/%s' %
                             (uuid, 'start'), expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch('watcher.common.policy.enforce')
    def test_start_action_plan(self, mock_policy):
        mock_policy.return_value = True
        action = obj_utils.create_test_action(
            self.context, id=1)
        self.action_plan.state = objects.action_plan.State.SUCCEEDED
        response = self.post('/v1/action_plans/%s/%s/'
                             % (self.action_plan.uuid, 'start'),
                             expect_errors=True)
        self.assertEqual(HTTPStatus.OK, response.status_int)
        act_response = self.get_json(
            '/actions/%s' % action.uuid,
            expect_errors=True)
        self.assertEqual(HTTPStatus.OK, act_response.status_int)
        self.assertEqual('PENDING', act_response.json['state'])
        self.assertEqual('application/json', act_response.content_type)


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(
            self.context, state=objects.action_plan.State.RECOMMENDED)
        p = mock.patch.object(db_api.BaseConnection, 'update_action_plan')
        self.mock_action_plan_update = p.start()
        self.mock_action_plan_update.side_effect = \
            self._simulate_rpc_action_plan_update
        self.addCleanup(p.stop)

    def _simulate_rpc_action_plan_update(self, action_plan):
        action_plan.save()
        return action_plan

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_denied(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_state = objects.action_plan.State.DELETED
        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertNotEqual(new_state, response['state'])

        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'}],
            expect_errors=True)

        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_replace_non_existent_action_plan_denied(self):
        response = self.patch_json(
            '/action_plans/%s' % utils.generate_uuid(),
            [{'path': '/state',
              'value': objects.action_plan.State.PENDING,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_add_non_existent_property_denied(self):
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_denied(self):
        # We should not be able to remove the state of an action plan
        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertIsNotNone(response['state'])

        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/state', 'op': 'remove'}],
            expect_errors=True)

        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_uuid_denied(self):
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/uuid', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property_denied(self):
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(aapi.ApplierAPI, 'launch_action_plan')
    def test_replace_state_pending_ok(self, applier_mock):
        new_state = objects.action_plan.State.PENDING
        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertNotEqual(new_state, response['state'])
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/state', 'value': new_state,
              'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.OK, response.status_code)
        applier_mock.assert_called_once_with(mock.ANY,
                                             self.action_plan.uuid)


ALLOWED_TRANSITIONS = [
    {"original_state": objects.action_plan.State.RECOMMENDED,
     "new_state": objects.action_plan.State.PENDING},
    {"original_state": objects.action_plan.State.RECOMMENDED,
     "new_state": objects.action_plan.State.CANCELLED},
    {"original_state": objects.action_plan.State.ONGOING,
     "new_state": objects.action_plan.State.CANCELLING},
    {"original_state": objects.action_plan.State.PENDING,
     "new_state": objects.action_plan.State.CANCELLED},
]


class TestPatchStateTransitionDenied(api_base.FunctionalTest):

    STATES = [
        ap_state for ap_state in objects.action_plan.State.__dict__
        if not ap_state.startswith("_")
    ]

    scenarios = [
        (
            "%s -> %s" % (original_state, new_state),
            {"original_state": original_state,
             "new_state": new_state},
        )
        for original_state, new_state
        in list(itertools.product(STATES, STATES))
        # from DELETED to ...
        # NOTE: Any state transition from DELETED (To RECOMMENDED, PENDING,
        # ONGOING, CANCELLED, SUCCEEDED and FAILED) will cause a 404 Not Found
        # because we cannot retrieve them with a GET (soft_deleted state).
        # This is the reason why they are not listed here but they have a
        # special test to cover it
        if original_state != objects.action_plan.State.DELETED and
        original_state != new_state and
        {"original_state": original_state,
         "new_state": new_state} not in ALLOWED_TRANSITIONS
    ]

    def setUp(self):
        super(TestPatchStateTransitionDenied, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)

    @mock.patch.object(
        db_api.BaseConnection, 'update_action_plan',
        mock.Mock(side_effect=lambda ap: ap.save() or ap))
    def test_replace_state_pending_denied(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context, state=self.original_state)

        initial_ap = self.get_json('/action_plans/%s' % action_plan.uuid)
        response = self.patch_json(
            '/action_plans/%s' % action_plan.uuid,
            [{'path': '/state', 'value': self.new_state,
              'op': 'replace'}],
            expect_errors=True)
        updated_ap = self.get_json('/action_plans/%s' % action_plan.uuid)

        self.assertNotEqual(self.new_state, initial_ap['state'])
        self.assertEqual(self.original_state, updated_ap['state'])
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPatchStateTransitionOk(api_base.FunctionalTest):

    scenarios = [
        (
            "%s -> %s" % (transition["original_state"],
                          transition["new_state"]),
            transition
        )
        for transition in ALLOWED_TRANSITIONS
    ]

    def setUp(self):
        super(TestPatchStateTransitionOk, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)

    @mock.patch.object(
        db_api.BaseConnection, 'update_action_plan',
        mock.Mock(side_effect=lambda ap: ap.save() or ap))
    @mock.patch.object(aapi.ApplierAPI, 'launch_action_plan', mock.Mock())
    def test_replace_state_pending_ok(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context, state=self.original_state)

        initial_ap = self.get_json('/action_plans/%s' % action_plan.uuid)

        response = self.patch_json(
            '/action_plans/%s' % action_plan.uuid,
            [{'path': '/state', 'value': self.new_state, 'op': 'replace'}])
        updated_ap = self.get_json('/action_plans/%s' % action_plan.uuid)
        self.assertNotEqual(self.new_state, initial_ap['state'])
        self.assertEqual(self.new_state, updated_ap['state'])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.OK, response.status_code)


class TestActionPlanPolicyEnforcement(api_base.FunctionalTest):

    def setUp(self):
        super(TestActionPlanPolicyEnforcement, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            rule: "rule:default"})
        response = func(*arg, **kwarg)
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            jsonutils.loads(response.json['error_message'])['faultstring'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "action_plan:get_all", self.get_json, '/action_plans',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        self._common_policy_check(
            "action_plan:get", self.get_json,
            '/action_plans/%s' % action_plan.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "action_plan:detail", self.get_json,
            '/action_plans/detail',
            expect_errors=True)

    def test_policy_disallow_update(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        self._common_policy_check(
            "action_plan:update", self.patch_json,
            '/action_plans/%s' % action_plan.uuid,
            [{'path': '/state',
              'value': objects.action_plan.State.DELETED,
              'op': 'replace'}],
            expect_errors=True)

    def test_policy_disallow_delete(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        self._common_policy_check(
            "action_plan:delete", self.delete,
            '/action_plans/%s' % action_plan.uuid, expect_errors=True)


class TestActionPlanPolicyEnforcementWithAdminContext(TestListActionPlan,
                                                      api_base.AdminRoleTest):

    def setUp(self):
        super(TestActionPlanPolicyEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "action_plan:delete": "rule:default",
            "action_plan:detail": "rule:default",
            "action_plan:get": "rule:default",
            "action_plan:get_all": "rule:default",
            "action_plan:update": "rule:default",
            "action_plan:start": "rule:default"})
