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

from oslo_config import cfg
from oslo_serialization import jsonutils
from urllib import parse as urlparse

from watcher.common import utils
from watcher.tests.api import base as api_base
from watcher.tests.objects import utils as obj_utils


class TestListGoal(api_base.FunctionalTest):

    def _assert_goal_fields(self, goal):
        goal_fields = ['uuid', 'name', 'display_name',
                       'efficacy_specification']
        for field in goal_fields:
            self.assertIn(field, goal)

    def test_one(self):
        goal = obj_utils.create_test_goal(self.context)
        response = self.get_json('/goals')
        self.assertEqual(goal.uuid, response['goals'][0]["uuid"])
        self._assert_goal_fields(response['goals'][0])

    def test_get_one_by_uuid(self):
        goal = obj_utils.create_test_goal(self.context)
        response = self.get_json('/goals/%s' % goal.uuid)
        self.assertEqual(goal.uuid, response["uuid"])
        self.assertEqual(goal.name, response["name"])
        self._assert_goal_fields(response)

    def test_get_one_by_name(self):
        goal = obj_utils.create_test_goal(self.context)
        response = self.get_json(urlparse.quote(
            '/goals/%s' % goal['name']))
        self.assertEqual(goal.uuid, response['uuid'])
        self._assert_goal_fields(response)

    def test_get_one_soft_deleted(self):
        goal = obj_utils.create_test_goal(self.context)
        goal.soft_delete()
        response = self.get_json(
            '/goals/%s' % goal['uuid'],
            headers={'X-Show-Deleted': 'True'})
        self.assertEqual(goal.uuid, response['uuid'])
        self._assert_goal_fields(response)

        response = self.get_json(
            '/goals/%s' % goal['uuid'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_detail(self):
        goal = obj_utils.create_test_goal(self.context)
        response = self.get_json('/goals/detail')
        self.assertEqual(goal.uuid, response['goals'][0]["uuid"])
        self._assert_goal_fields(response['goals'][0])

    def test_detail_against_single(self):
        goal = obj_utils.create_test_goal(self.context)
        response = self.get_json('/goals/%s/detail' % goal.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        goal_list = []
        for idx in range(1, 6):
            goal = obj_utils.create_test_goal(
                self.context, id=idx,
                uuid=utils.generate_uuid(),
                name='GOAL_{0}'.format(idx))
            goal_list.append(goal.uuid)
        response = self.get_json('/goals')
        self.assertGreater(len(response['goals']), 2)

    def test_many_without_soft_deleted(self):
        goal_list = []
        for id_ in [1, 2, 3]:
            goal = obj_utils.create_test_goal(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='GOAL_{0}'.format(id_))
            goal_list.append(goal.uuid)
        for id_ in [4, 5]:
            goal = obj_utils.create_test_goal(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='GOAL_{0}'.format(id_))
            goal.soft_delete()
        response = self.get_json('/goals')
        self.assertEqual(3, len(response['goals']))
        uuids = [s['uuid'] for s in response['goals']]
        self.assertEqual(sorted(goal_list), sorted(uuids))

    def test_goals_collection_links(self):
        for idx in range(1, 6):
            obj_utils.create_test_goal(
                self.context, id=idx,
                uuid=utils.generate_uuid(),
                name='GOAL_{0}'.format(idx))
        response = self.get_json('/goals/?limit=2')
        self.assertEqual(2, len(response['goals']))

    def test_goals_collection_links_default_limit(self):
        for idx in range(1, 6):
            obj_utils.create_test_goal(
                self.context, id=idx,
                uuid=utils.generate_uuid(),
                name='GOAL_{0}'.format(idx))
        cfg.CONF.set_override('max_limit', 3, 'api')
        response = self.get_json('/goals')
        self.assertEqual(3, len(response['goals']))

    def test_many_with_sort_key_uuid(self):
        goal_list = []
        for idx in range(1, 6):
            goal = obj_utils.create_test_goal(
                self.context, id=idx,
                uuid=utils.generate_uuid(),
                name='GOAL_{0}'.format(idx))
            goal_list.append(goal.uuid)

        response = self.get_json('/goals/?sort_key=uuid')

        self.assertEqual(5, len(response['goals']))
        uuids = [s['uuid'] for s in response['goals']]
        self.assertEqual(sorted(goal_list), uuids)

    def test_sort_key_validation(self):
        response = self.get_json(
            '/goals?sort_key=%s' % 'bad_name',
            expect_errors=True)
        self.assertEqual(400, response.status_int)


class TestGoalPolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            rule: "rule:default"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            jsonutils.loads(response.json['error_message'])['faultstring'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "goal:get_all", self.get_json, '/goals',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        goal = obj_utils.create_test_goal(self.context)
        self._common_policy_check(
            "goal:get", self.get_json,
            '/goals/%s' % goal.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "goal:detail", self.get_json,
            '/goals/detail',
            expect_errors=True)


class TestGoalPolicyEnforcementWithAdminContext(TestListGoal,
                                                api_base.AdminRoleTest):

    def setUp(self):
        super(TestGoalPolicyEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "goal:detail": "rule:default",
            "goal:get_all": "rule:default",
            "goal:get_one": "rule:default"})
