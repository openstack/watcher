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

import json

from oslo_config import cfg
from six.moves.urllib import parse as urlparse

from watcher.common import utils
from watcher.tests.api import base as api_base
from watcher.tests.objects import utils as obj_utils


class TestListStrategy(api_base.FunctionalTest):

    def _assert_strategy_fields(self, strategy):
        strategy_fields = ['uuid', 'name', 'display_name', 'goal_uuid']
        for field in strategy_fields:
            self.assertIn(field, strategy)

    def test_one(self):
        strategy = obj_utils.create_test_strategy(self.context)
        response = self.get_json('/strategies')
        self.assertEqual(strategy.uuid, response['strategies'][0]["uuid"])
        self._assert_strategy_fields(response['strategies'][0])

    def test_get_one_by_uuid(self):
        strategy = obj_utils.create_test_strategy(self.context)
        response = self.get_json('/strategies/%s' % strategy.uuid)
        self.assertEqual(strategy.uuid, response["uuid"])
        self.assertEqual(strategy.name, response["name"])
        self._assert_strategy_fields(response)

    def test_get_one_by_name(self):
        strategy = obj_utils.create_test_strategy(self.context)
        response = self.get_json(urlparse.quote(
            '/strategies/%s' % strategy['name']))
        self.assertEqual(strategy.uuid, response['uuid'])
        self._assert_strategy_fields(response)

    def test_get_one_soft_deleted(self):
        strategy = obj_utils.create_test_strategy(self.context)
        strategy.soft_delete()
        response = self.get_json(
            '/strategies/%s' % strategy['uuid'],
            headers={'X-Show-Deleted': 'True'})
        self.assertEqual(strategy.uuid, response['uuid'])
        self._assert_strategy_fields(response)

        response = self.get_json(
            '/strategies/%s' % strategy['uuid'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_detail(self):
        obj_utils.create_test_goal(self.context)
        strategy = obj_utils.create_test_strategy(self.context)
        response = self.get_json('/strategies/detail')
        self.assertEqual(strategy.uuid, response['strategies'][0]["uuid"])
        self._assert_strategy_fields(response['strategies'][0])
        for strategy in response['strategies']:
            self.assertTrue(
                all(val is not None for key, val in strategy.items()
                    if key in ['uuid', 'name', 'display_name', 'goal_uuid']))

    def test_detail_against_single(self):
        strategy = obj_utils.create_test_strategy(self.context)
        response = self.get_json('/strategies/%s/detail' % strategy.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        obj_utils.create_test_goal(self.context)
        strategy_list = []
        for idx in range(1, 6):
            strategy = obj_utils.create_test_strategy(
                self.context, id=idx,
                uuid=utils.generate_uuid(),
                name='STRATEGY_{0}'.format(idx))
            strategy_list.append(strategy.uuid)
        response = self.get_json('/strategies')
        self.assertEqual(5, len(response['strategies']))
        for strategy in response['strategies']:
            self.assertTrue(
                all(val is not None for key, val in strategy.items()
                    if key in ['uuid', 'name', 'display_name', 'goal_uuid']))

    def test_many_without_soft_deleted(self):
        strategy_list = []
        for id_ in [1, 2, 3]:
            strategy = obj_utils.create_test_strategy(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='STRATEGY_{0}'.format(id_))
            strategy_list.append(strategy.uuid)
        for id_ in [4, 5]:
            strategy = obj_utils.create_test_strategy(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='STRATEGY_{0}'.format(id_))
            strategy.soft_delete()
        response = self.get_json('/strategies')
        self.assertEqual(3, len(response['strategies']))
        uuids = [s['uuid'] for s in response['strategies']]
        self.assertEqual(sorted(strategy_list), sorted(uuids))

    def test_strategies_collection_links(self):
        for idx in range(1, 6):
            obj_utils.create_test_strategy(
                self.context, id=idx,
                uuid=utils.generate_uuid(),
                name='STRATEGY_{0}'.format(idx))
        response = self.get_json('/strategies/?limit=2')
        self.assertEqual(2, len(response['strategies']))

    def test_strategies_collection_links_default_limit(self):
        for idx in range(1, 6):
            obj_utils.create_test_strategy(
                self.context, id=idx,
                uuid=utils.generate_uuid(),
                name='STRATEGY_{0}'.format(idx))
        cfg.CONF.set_override('max_limit', 3, 'api', enforce_type=True)
        response = self.get_json('/strategies')
        self.assertEqual(3, len(response['strategies']))

    def test_filter_by_goal_uuid(self):
        goal1 = obj_utils.create_test_goal(
            self.context,
            id=1,
            uuid=utils.generate_uuid(),
            name='My_Goal 1')
        goal2 = obj_utils.create_test_goal(
            self.context,
            id=2,
            uuid=utils.generate_uuid(),
            name='My Goal 2')

        for id_ in range(1, 3):
            obj_utils.create_test_strategy(
                self.context, id=id_,
                uuid=utils.generate_uuid(),
                goal_id=goal1['id'])
        for id_ in range(3, 5):
            obj_utils.create_test_strategy(
                self.context, id=id_,
                uuid=utils.generate_uuid(),
                goal_id=goal2['id'])

        response = self.get_json('/strategies/?goal=%s' % goal1['uuid'])

        strategies = response['strategies']
        self.assertEqual(2, len(strategies))
        for strategy in strategies:
            self.assertEqual(goal1['uuid'], strategy['goal_uuid'])

    def test_filter_by_goal_name(self):
        goal1 = obj_utils.create_test_goal(
            self.context,
            id=1,
            uuid=utils.generate_uuid(),
            name='My_Goal 1')
        goal2 = obj_utils.create_test_goal(
            self.context,
            id=2,
            uuid=utils.generate_uuid(),
            name='My Goal 2')

        for id_ in range(1, 3):
            obj_utils.create_test_strategy(
                self.context, id=id_,
                uuid=utils.generate_uuid(),
                goal_id=goal1['id'])
        for id_ in range(3, 5):
            obj_utils.create_test_strategy(
                self.context, id=id_,
                uuid=utils.generate_uuid(),
                goal_id=goal2['id'])

        response = self.get_json('/strategies/?goal=%s' % goal1['name'])

        strategies = response['strategies']
        self.assertEqual(2, len(strategies))
        for strategy in strategies:
            self.assertEqual(goal1['uuid'], strategy['goal_uuid'])


class TestStrategyPolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            rule: "rule:defaut"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            json.loads(response.json['error_message'])['faultstring'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "strategy:get_all", self.get_json, '/strategies',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        strategy = obj_utils.create_test_strategy(self.context)
        self._common_policy_check(
            "strategy:get", self.get_json,
            '/strategies/%s' % strategy.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "strategy:detail", self.get_json,
            '/strategies/detail',
            expect_errors=True)


class TestStrategyEnforcementWithAdminContext(TestListStrategy,
                                              api_base.AdminRoleTest):

    def setUp(self):
        super(TestStrategyEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "strategy:detail": "rule:default",
            "strategy:get": "rule:default",
            "strategy:get_all": "rule:default"})
