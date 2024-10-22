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
        super(TestListAction, self).setUp()
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

    def test_one(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions')
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])

    def test_one_soft_deleted(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        action.soft_delete()
        response = self.get_json('/actions',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])

        response = self.get_json('/actions')
        self.assertEqual([], response['actions'])

    def test_get_one(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions/%s' % action['uuid'])
        self.assertEqual(action.uuid, response['uuid'])
        self.assertEqual(action.action_type, response['action_type'])
        self.assertEqual(action.input_parameters, response['input_parameters'])
        self._assert_action_fields(response)

    def test_get_one_soft_deleted(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        action.soft_delete()
        response = self.get_json('/actions/%s' % action['uuid'],
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action.uuid, response['uuid'])
        self._assert_action_fields(response)

        response = self.get_json('/actions/%s' % action['uuid'],
                                 expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)

    def test_detail(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions/detail')
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])

    def test_detail_soft_deleted(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        action.soft_delete()
        response = self.get_json('/actions/detail',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action.uuid, response['actions'][0]["uuid"])
        self._assert_action_fields(response['actions'][0])

        response = self.get_json('/actions/detail')
        self.assertEqual([], response['actions'])

    def test_detail_against_single(self):
        action = obj_utils.create_test_action(self.context, parents=None)
        response = self.get_json('/actions/%s/detail' % action['uuid'],
                                 expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_int)

    def test_many(self):
        action_list = []
        for id_ in range(5):
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid())
            action_list.append(action.uuid)
        response = self.get_json('/actions')
        self.assertEqual(len(action_list), len(response['actions']))
        uuids = [s['uuid'] for s in response['actions']]
        self.assertEqual(sorted(action_list), sorted(uuids))

    def test_many_with_action_plan_uuid(self):
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

    def test_filter_by_audit_uuid(self):
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
            name='My Audit {0}'.format(2))
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

    def test_filter_by_action_plan_uuid(self):
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

    def test_details_and_filter_by_action_plan_uuid(self):
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

    def test_details_and_filter_by_audit_uuid(self):
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

    def test_filter_by_action_plan_and_audit_uuids(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context,
            uuid=utils.generate_uuid(),
            audit_id=self.audit.id)
        url = '/actions?action_plan_uuid=%s&audit_uuid=%s' % (
            action_plan.uuid, self.audit.uuid)
        response = self.get_json(url, expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)

    def test_many_with_sort_key_uuid(self):
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

    def test_many_with_sort_key_action_plan_uuid(self):
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
                '/actions?sort_key={0}&sort_dir={1}'
                .format('action_plan_uuid', direction))

            action_plan_uuids = \
                [s['action_plan_uuid'] for s in response['actions']]

            self.assertEqual(
                sorted(action_plans_uuid_list, reverse=(direction == 'desc')),
                action_plan_uuids,
                message='Failed on %s direction' % direction)

    def test_sort_key_validation(self):
        response = self.get_json(
            '/actions?sort_key=%s' % 'bad_name',
            expect_errors=True)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_int)

    def test_many_with_soft_deleted_action_plan_uuid(self):
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
            set([act.as_dict()['uuid'] for act in ap2_action_list]),
            set([act['uuid'] for act in response['actions']
                 if act['action_plan_uuid'] == action_plan2.uuid]))

    def test_many_with_parents(self):
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

    def test_many_without_soft_deleted(self):
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

    def test_many_with_soft_deleted(self):
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

    def test_links(self):
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

    def test_collection_links(self):
        parents = None
        for id_ in range(5):
            action = obj_utils.create_test_action(self.context, id=id_,
                                                  uuid=utils.generate_uuid(),
                                                  parents=parents)
            parents = [action.uuid]
        response = self.get_json('/actions/?limit=3')
        self.assertEqual(3, len(response['actions']))

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_action(self.context, id=id_,
                                         uuid=utils.generate_uuid())
        response = self.get_json('/actions')
        self.assertEqual(3, len(response['actions']))


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)
        obj_utils.create_test_action_plan(self.context)
        self.action = obj_utils.create_test_action(self.context, parents=None)
        p = mock.patch.object(db_api.BaseConnection, 'update_action')
        self.mock_action_update = p.start()
        self.mock_action_update.side_effect = self._simulate_rpc_action_update
        self.addCleanup(p.stop)

    def _simulate_rpc_action_update(self, action):
        action.save()
        return action

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_patch_not_allowed(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        new_state = objects.audit.State.SUCCEEDED
        response = self.get_json('/actions/%s' % self.action.uuid)
        self.assertNotEqual(new_state, response['state'])

        response = self.patch_json(
            '/actions/%s' % self.action.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_int)
        self.assertTrue(response.json['error_message'])


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        self.goal = obj_utils.create_test_goal(self.context)
        self.strategy = obj_utils.create_test_strategy(self.context)
        self.audit = obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(self.context)
        self.action = obj_utils.create_test_action(self.context, parents=None)
        p = mock.patch.object(db_api.BaseConnection, 'update_action')
        self.mock_action_update = p.start()
        self.mock_action_update.side_effect = self._simulate_rpc_action_update
        self.addCleanup(p.stop)

    def _simulate_rpc_action_update(self, action):
        action.save()
        return action

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_delete_action_not_allowed(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        response = self.delete('/actions/%s' % self.action.uuid,
                               expect_errors=True)
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestActionPolicyEnforcement(api_base.FunctionalTest):

    def setUp(self):
        super(TestActionPolicyEnforcement, self).setUp()
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


class TestActionPolicyEnforcementWithAdminContext(TestListAction,
                                                  api_base.AdminRoleTest):

    def setUp(self):
        super(TestActionPolicyEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "action:detail": "rule:default",
            "action:get": "rule:default",
            "action:get_all": "rule:default"})
