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

import fixtures
import itertools

from http import HTTPStatus
from oslo_config import cfg
from oslo_serialization import jsonutils
from wsme import types as wtypes

from watcher.api.controllers.v1 import action as api_action
from watcher.common import utils
from watcher.db import api as db_api
from watcher import objects
from watcher.tests.api import base as api_base
from watcher.tests.api import utils as api_utils
from watcher.tests import base
from watcher.tests.db import utils as db_utils
from watcher.tests.objects import utils as obj_utils


def post_get_test_action(**kw):
    action = api_utils.action_post_data(**kw)
    action_plan = db_utils.get_test_action_plan()
    del action['action_plan_id']
    action['action_plan_uuid'] = kw.get('action_plan_uuid',
                                        action_plan['uuid'])
    action['parents'] = None
    return action


class TestActionObject(base.TestCase):

    def test_action_init(self):
        action_dict = api_utils.action_post_data(action_plan_id=None,
                                                 parents=None)
        del action_dict['state']
        action = api_action.Action(**action_dict)
        self.assertEqual(wtypes.Unset, action.state)


class TestListAction(api_base.FunctionalTest):

    def setUp(self):
        super().setUp()
        self.goal = obj_utils.create_test_goal(self.context)
        self.strategy = obj_utils.create_test_strategy(self.context)
        self.audit = obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(self.context)

    def test_empty(self):
        response = self.get_json('/actions')
        self.assertEqual([], response['actions'])

    def _assert_action_fields(self, action):
        action_fields = ['uuid', 'state', 'action_plan_uuid', 'action_type']
        for field in action_fields:
            self.assertIn(field, action)

    def test_list(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions')
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])
        self.assertNotIn('status_message', response['actions'][0])

    def test_list_with_status_message(self):
        action = obj_utils.create_test_action(
            self.context, parents=None, status_message='Fake message')
        response = self.get_json(
            '/actions', headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])
        # status_message is not in the basic actions list
        self.assertNotIn('status_message', response['actions'][0])

    def test_list_detail_with_hidden_status_message(self):
        action = obj_utils.create_test_action(
            self.context, status_message='Fake message', parents=None)
        response = self.get_json('/actions/detail')
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])
        self.assertNotIn('status_message', response['actions'][0])

    def test_list_detail_with_status_message(self):
        action = obj_utils.create_test_action(
            self.context, status_message='Fake message', parents=None)
        response = self.get_json(
            '/actions/detail',
            headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])
        self.assertEqual(
            'Fake message', response['actions'][0]["status_message"])

    def test_list_soft_deleted(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        action.soft_delete()
        response = self.get_json('/actions',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])

        response = self.get_json('/actions')
        self.assertEqual([], response['actions'])

    def test_show(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions/%s' % action['uuid'])
        self.assertEqual(action.uuid, response['uuid'])
        self.assertEqual(action.action_type, response['action_type'])
        self.assertEqual(action.input_parameters, response['input_parameters'])
        self.assertNotIn('status_message', response)
        self._assert_action_fields(response)

    def test_show_with_status_message(self):
        action = obj_utils.create_test_action(
            self.context, parents=None, status_message='test')
        response = self.get_json(
            '/actions/%s' % action['uuid'],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual(action.uuid, response['uuid'])
        self.assertEqual(action.action_type, response['action_type'])
        self.assertEqual(action.input_parameters, response['input_parameters'])
        self.assertEqual('test', response['status_message'])
        self._assert_action_fields(response)

    def test_show_with_hidden_status_message(self):
        action = obj_utils.create_test_action(
            self.context, parents=None, status_message='test')
        response = self.get_json(
            '/actions/%s' % action['uuid'],
            headers={'OpenStack-API-Version': 'infra-optim 1.4'})
        self.assertEqual(action.uuid, response['uuid'])
        self.assertEqual(action.action_type, response['action_type'])
        self.assertEqual(action.input_parameters, response['input_parameters'])
        self.assertNotIn('status_message', response)
        self._assert_action_fields(response)

    def test_show_with_empty_status_message(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json(
            '/actions/%s' % action['uuid'],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual(action.uuid, response['uuid'])
        self.assertEqual(action.action_type, response['action_type'])
        self.assertEqual(action.input_parameters, response['input_parameters'])
        self.assertIsNone(response['status_message'])
        self._assert_action_fields(response)

    def test_show_soft_deleted(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        action.soft_delete()
        response = self.get_json('/actions/%s' % action['uuid'],
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action.uuid, response['uuid'])
        self._assert_action_fields(response)

        response = self.get_json('/actions/%s' % action['uuid'],
                                 expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)

    def test_list_detail(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions/detail')
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])

    def test_list_detail_soft_deleted(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        action.soft_delete()
        response = self.get_json('/actions/detail',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])

        response = self.get_json('/actions/detail')
        self.assertEqual([], response['actions'])

    def test_show_detail(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions/%s/detail' % action['uuid'],
                                 expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)

    def test_list_multiple_actions(self):
        action_list = []
        for id_ in range(5):
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid())
            action_list.append(action.uuid)
        response = self.get_json('/actions')
        self.assertEqual(len(action_list), len(response['actions']))
        uuids = [s['uuid'] for s in response['actions']]
        self.assertEqual(sorted(action_list), sorted(uuids))

    def test_list_with_action_plan_uuid(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context,
            id=2,
            uuid=utils.generate_uuid(),
            audit_id=1)
        action_list = []
        for id_ in range(5):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=2,
                uuid=utils.generate_uuid())
            action_list.append(action.uuid)
        response = self.get_json('/actions')
        self.assertEqual(len(action_list), len(response['actions']))
        for action in response['actions']:
            self.assertEqual(action_plan.uuid, action['action_plan_uuid'])

    def test_list_filter_by_audit_uuid(self):
        action_plan_1 = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid())
        action_list = []

        for id_ in range(3):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan_1.id,
                uuid=utils.generate_uuid())
            action_list.append(action.uuid)

        audit2 = obj_utils.create_test_audit(
            self.context, id=2, uuid=utils.generate_uuid(),
            name='My Audit {}'.format(2))
        action_plan_2 = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=audit2.id)

        for id_ in range(4, 5, 6):
            obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan_2.id,
                uuid=utils.generate_uuid())

        response = self.get_json('/actions?audit_uuid=%s' % self.audit.uuid)
        self.assertEqual(len(action_list), len(response['actions']))
        for action in response['actions']:
            self.assertEqual(action_plan_1.uuid, action['action_plan_uuid'])

    def test_list_filter_by_action_plan_uuid(self):
        action_plan_1 = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)
        action_list = []

        for id_ in range(3):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan_1.id,
                uuid=utils.generate_uuid())
            action_list.append(action.uuid)

        action_plan_2 = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)

        for id_ in range(4, 5, 6):
            obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan_2.id,
                uuid=utils.generate_uuid())

        response = self.get_json(
            '/actions?action_plan_uuid=%s' % action_plan_1.uuid)
        self.assertEqual(len(action_list), len(response['actions']))
        for action in response['actions']:
            self.assertEqual(action_plan_1.uuid, action['action_plan_uuid'])

        response = self.get_json(
            '/actions?action_plan_uuid=%s' % action_plan_2.uuid)
        for action in response['actions']:
            self.assertEqual(action_plan_2.uuid, action['action_plan_uuid'])

    def test_list_details_and_filter_by_action_plan_uuid(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)

        for id_ in range(1, 3):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan.id,
                uuid=utils.generate_uuid())

        response = self.get_json(
            '/actions/detail?action_plan_uuid=%s' % action_plan.uuid)
        for action in response['actions']:
            self.assertEqual(action_plan.uuid, action['action_plan_uuid'])

    def test_list_details_and_filter_by_audit_uuid(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)

        for id_ in range(1, 3):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan.id,
                uuid=utils.generate_uuid())

        response = self.get_json(
            '/actions/detail?audit_uuid=%s' % self.audit.uuid)
        for action in response['actions']:
            self.assertEqual(action_plan.uuid, action['action_plan_uuid'])

    def test_list_filter_by_action_plan_and_audit_uuids(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)
        url = '/actions?action_plan_uuid=%s&audit_uuid=%s' % (
            action_plan.uuid, self.audit.uuid)
        response = self.get_json(url, expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)

    def test_list_with_sort_key_uuid(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)

        actions_list = []
        for id_ in range(1, 3):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan.id,
                uuid=utils.generate_uuid())
            actions_list.append(action)

        response = self.get_json('/actions?sort_key=%s' % 'uuid')
        names = [s['uuid'] for s in response['actions']]

        self.assertEqual(
            sorted([a.uuid for a in actions_list]),
            names)

    def test_list_with_sort_key_action_plan_uuid(self):
        action_plan_1 = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)

        action_plan_2 = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)

        action_plans_uuid_list = []
        for id_, action_plan_id in enumerate(itertools.chain.from_iterable([
                itertools.repeat(action_plan_1.id, 3),
                itertools.repeat(action_plan_2.id, 2)]), 1):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan_id,
                uuid=utils.generate_uuid())
            action_plans_uuid_list.append(action.action_plan.uuid)

        for direction in ['asc', 'desc']:
            response = self.get_json(
                '/actions?sort_key={}&sort_dir={}'
                .format('action_plan_uuid', direction))

            action_plan_uuids = \
                [s['action_plan_uuid'] for s in response['actions']]

            self.assertEqual(
                sorted(action_plans_uuid_list, reverse=(direction == 'desc')),
                action_plan_uuids,
                message='Failed on %s direction' % direction)

    def test_list_sort_key_validation(self):
        response = self.get_json(
            '/actions?sort_key=%s' % 'bad_name',
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)

    def test_list_with_soft_deleted_action_plan_uuid(self):
        action_plan1 = obj_utils.create_test_action_plan(
            self.context,
            id=2,
            uuid=utils.generate_uuid(),
            audit_id=1)
        action_plan2 = obj_utils.create_test_action_plan(
            self.context,
            id=3,
            uuid=utils.generate_uuid(),
            audit_id=1)

        ap1_action_list = []
        ap2_action_list = []

        for id_ in range(0, 2):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan1.id,
                uuid=utils.generate_uuid())
            ap1_action_list.append(action)

        for id_ in range(2, 4):
            action = obj_utils.create_test_action(
                self.context, id=id_,
                action_plan_id=action_plan2.id,
                uuid=utils.generate_uuid())
            ap2_action_list.append(action)

        action_plan1.state = objects.action_plan.State.CANCELLED
        action_plan1.save()
        self.delete('/action_plans/%s' % action_plan1.uuid)

        response = self.get_json('/actions')
        # We deleted the actions from the 1st action plan so we've got 2 left
        self.assertEqual(len(ap2_action_list), len(response['actions']))

        # We deleted them so that's normal
        self.assertEqual([],
                         [act for act in response['actions']
                          if act['action_plan_uuid'] == action_plan1.uuid])

        # Here are the 2 actions left
        self.assertEqual(
            {act.as_dict()['uuid'] for act in ap2_action_list},
            {act['uuid'] for act in response['actions']
             if act['action_plan_uuid'] == action_plan2.uuid})

    def test_list_with_parents(self):
        action_list = []
        for id_ in range(5):
            if id_ > 0:
                action = obj_utils.create_test_action(
                    self.context, id=id_, uuid=utils.generate_uuid(),
                    parents=[action_list[id_ - 1]])
            else:
                action = obj_utils.create_test_action(
                    self.context, id=id_, uuid=utils.generate_uuid(),
                    parents=[])
            action_list.append(action.uuid)
        response = self.get_json('/actions')
        response_actions = response['actions']
        for id_ in range(4):
            self.assertEqual(response_actions[id_]['uuid'],
                             response_actions[id_ + 1]['parents'][0])

    def test_list_without_soft_deleted(self):
        action_list = []
        for id_ in [1, 2, 3]:
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid())
            action_list.append(action.uuid)
        for id_ in [4, 5]:
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid())
            action.soft_delete()
        response = self.get_json('/actions')
        self.assertEqual(3, len(response['actions']))
        uuids = [s['uuid'] for s in response['actions']]
        self.assertEqual(sorted(action_list), sorted(uuids))

    def test_list_with_soft_deleted(self):
        action_list = []
        for id_ in [1, 2, 3]:
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid())
            action_list.append(action.uuid)
        for id_ in [4, 5]:
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid())
            action.soft_delete()
            action_list.append(action.uuid)
        response = self.get_json('/actions',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(5, len(response['actions']))
        uuids = [s['uuid'] for s in response['actions']]
        self.assertEqual(sorted(action_list), sorted(uuids))

    def test_show_with_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_action(self.context, id=1, uuid=uuid)
        response = self.get_json('/actions/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for link in response['links']:
            bookmark = link['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(
                link['href'], bookmark=bookmark))

    def test_list_with_limit(self):
        parents = None
        for id_ in range(5):
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid(),
                                                  parents=parents)
            parents = [action.uuid]
        response = self.get_json('/actions/?limit=3')
        self.assertEqual(3, len(response['actions']))

    def test_list_with_default_max_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_action(self.context, id=id_,
                                         uuid=utils.generate_uuid())
        response = self.get_json('/actions')
        self.assertEqual(3, len(response['actions']))


class TestPatchAction(api_base.FunctionalTest):

    def setUp(self):
        super().setUp()
        self.goal = obj_utils.create_test_goal(self.context)
        self.strategy = obj_utils.create_test_strategy(self.context)
        self.audit = obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(
            self.context,
            state=objects.action_plan.State.PENDING)
        self.action = obj_utils.create_test_action(self.context, parents=None)
        self.mock_action_update = self.useFixture(
            fixtures.MockPatchObject(
                db_api.BaseConnection, "update_action",
                autospec=False,
                side_effect=self._simulate_rpc_action_update)
        ).mock.return_value

    def _simulate_rpc_action_update(self, action):
        action.save()
        return action

    def test_patch_action_not_allowed_old_microversion(self):
        """Test that action patch is not allowed in older microversions"""
        new_state = objects.action.State.SKIPPED
        response = self.get_json('/actions/%s' % self.action.uuid)
        self.assertNotEqual(new_state, response['state'])

        # Test with API version 1.4 (should fail)
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.4'},
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_patch_action_allowed_new_microversion(self):
        """Test that action patch is allowed in microversion 1.5+"""
        new_state = objects.action.State.SKIPPED
        response = self.get_json('/actions/%s' % self.action.uuid)
        self.assertNotEqual(new_state, response['state'])

        # Test with API version 1.5 (should succeed)
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.OK, response.status_int)
        self.assertEqual(new_state, response.json['state'])
        self.assertEqual('Action skipped by user.',
                         response.json['status_message'])

    def test_patch_action_invalid_state_transition(self):
        """Test that invalid state transitions are rejected"""
        # Try to transition from PENDING to SUCCEEDED (should fail)
        new_state = objects.action.State.SUCCEEDED
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.CONFLICT, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
        self.assertIn("State transition not allowed: (PENDING -> SUCCEEDED)",
                      response.json['error_message'])

    def test_patch_action_skip_non_pending_ap(self):
        """Test transition conditions on parent actionplan

        The PENDING to SKIPPED transition is not allowed if
        the actionplan is not PENDING or RECOMMENDED state
        """
        self.action_plan.state = objects.action_plan.State.ONGOING
        self.action_plan.save()
        new_state = objects.action.State.SKIPPED
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'},
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.CONFLICT, response.status_int)
        self.assertTrue(response.json['error_message'])
        self.assertIn("State update not allowed for actionplan state: ONGOING",
                      response.json['error_message'])

    def test_patch_action_skip_transition_with_status_message(self):
        """Test that PENDING to SKIPPED transition is allowed"""
        new_state = objects.action.State.SKIPPED
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'},
             {'path': '/status_message', 'value': 'test message',
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.OK, response.status_int)
        self.assertEqual(new_state, response.json['state'])
        self.assertEqual(
            'Action skipped by user. Reason: test message',
            response.json['status_message'])

    def test_patch_action_invalid_state_value(self):
        """Test that invalid state values are rejected"""
        invalid_state = "INVALID_STATE"
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': invalid_state, 'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_patch_action_remove_status_message_not_allowed(self):
        """Test that remove fields is not allowed"""
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/status_message', 'op': 'remove'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
        self.assertIn("is a mandatory attribute and can not be removed",
                      response.json['error_message'])

    def test_patch_action_status_message_not_allowed(self):
        """Test status_message cannot be patched directly when not SKIPPED"""
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/status_message', 'value': 'test message',
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.CONFLICT, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertIn("status_message update only allowed when action state "
                      "is SKIPPED", response.json['error_message'])
        self.assertIsNone(self.action.status_message)

    def test_patch_action_one_allowed_one_not_allowed(self):
        """Test that status_message cannot be patched directly"""
        new_state = objects.action.State.SKIPPED
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'},
             {'path': '/action_plan_id', 'value': 56, 'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
        self.assertIn("\'/action_plan_id\' is not an allowed attribute and "
                      "can not be updated", response.json['error_message'])
        self.assertIsNone(self.action.status_message)

    def test_patch_action_status_message_allowed_when_skipped(self):
        """Test that status_message can be updated when action is SKIPPED"""
        # First transition to SKIPPED state
        new_state = objects.action.State.SKIPPED
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'},
             {'path': '/status_message', 'value': 'initial message',
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual(HTTPStatus.OK, response.status_int)
        self.assertEqual(new_state, response.json['state'])

        # Now update status_message while in SKIPPED state
        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/status_message', 'value': 'updated message',
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'})
        self.assertEqual(HTTPStatus.OK, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(new_state, response.json['state'])
        self.assertEqual(
            'Action skipped by user. Reason: updated message',
            response.json['status_message'])


class TestActionPolicyEnforcement(api_base.FunctionalTest):

    def setUp(self):
        super().setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)
        obj_utils.create_test_action_plan(self.context)

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
            "action:get_all", self.get_json, '/actions',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        action = obj_utils.create_test_action(self.context)
        self._common_policy_check(
            "action:get", self.get_json,
            '/actions/%s' % action.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "action:detail", self.get_json,
            '/actions/detail',
            expect_errors=True)

    def test_policy_disallow_patch(self):
        action = obj_utils.create_test_action(self.context)
        self._common_policy_check(
            "action:update", self.patch_json,
            '/actions/%s' % action.uuid,
            [{'path': '/state', 'value': objects.action.State.SKIPPED,
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'infra-optim 1.5'},
            expect_errors=True)


class TestActionPolicyEnforcementWithAdminContext(TestListAction,
                                                  api_base.AdminRoleTest):

    def setUp(self):
        super().setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "action:detail": "rule:default",
            "action:get": "rule:default",
            "action:get_all": "rule:default"})
