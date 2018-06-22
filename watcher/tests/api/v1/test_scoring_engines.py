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
from watcher.common import utils

from watcher.tests.api import base as api_base
from watcher.tests.objects import utils as obj_utils


class TestListScoringEngine(api_base.FunctionalTest):

    def _assert_scoring_engine_fields(self, scoring_engine):
        scoring_engine_fields = ['uuid', 'name', 'description']
        for field in scoring_engine_fields:
            self.assertIn(field, scoring_engine)

    def test_one(self):
        scoring_engine = obj_utils.create_test_scoring_engine(self.context)
        response = self.get_json('/scoring_engines')
        self.assertEqual(
            scoring_engine.name, response['scoring_engines'][0]['name'])
        self._assert_scoring_engine_fields(response['scoring_engines'][0])

    def test_get_one_soft_deleted(self):
        scoring_engine = obj_utils.create_test_scoring_engine(self.context)
        scoring_engine.soft_delete()
        response = self.get_json(
            '/scoring_engines/%s' % scoring_engine['name'],
            headers={'X-Show-Deleted': 'True'})
        self.assertEqual(scoring_engine.name, response['name'])
        self._assert_scoring_engine_fields(response)

        response = self.get_json(
            '/scoring_engines/%s' % scoring_engine['name'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_detail(self):
        obj_utils.create_test_goal(self.context)
        scoring_engine = obj_utils.create_test_scoring_engine(self.context)
        response = self.get_json('/scoring_engines/detail')
        self.assertEqual(
            scoring_engine.name, response['scoring_engines'][0]['name'])
        self._assert_scoring_engine_fields(response['scoring_engines'][0])
        for scoring_engine in response['scoring_engines']:
            self.assertTrue(
                all(val is not None for key, val in scoring_engine.items()
                    if key in ['uuid', 'name', 'description', 'metainfo']))

    def test_detail_against_single(self):
        scoring_engine = obj_utils.create_test_scoring_engine(self.context)
        response = self.get_json(
            '/scoring_engines/%s/detail' % scoring_engine.id,
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        scoring_engine_list = []
        for idx in range(1, 6):
            scoring_engine = obj_utils.create_test_scoring_engine(
                self.context, id=idx, uuid=utils.generate_uuid(),
                name=str(idx), description='SE_{0}'.format(idx))
            scoring_engine_list.append(scoring_engine.name)
        response = self.get_json('/scoring_engines')
        self.assertEqual(5, len(response['scoring_engines']))
        for scoring_engine in response['scoring_engines']:
            self.assertTrue(
                all(val is not None for key, val in scoring_engine.items()
                    if key in ['name', 'description', 'metainfo']))

    def test_many_without_soft_deleted(self):
        scoring_engine_list = []
        for id_ in [1, 2, 3]:
            scoring_engine = obj_utils.create_test_scoring_engine(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name=str(id_), description='SE_{0}'.format(id_))
            scoring_engine_list.append(scoring_engine.name)
        for id_ in [4, 5]:
            scoring_engine = obj_utils.create_test_scoring_engine(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name=str(id_), description='SE_{0}'.format(id_))
            scoring_engine.soft_delete()
        response = self.get_json('/scoring_engines')
        self.assertEqual(3, len(response['scoring_engines']))
        names = [s['name'] for s in response['scoring_engines']]
        self.assertEqual(sorted(scoring_engine_list), sorted(names))

    def test_scoring_engines_collection_links(self):
        for idx in range(1, 6):
            obj_utils.create_test_scoring_engine(
                self.context, id=idx, uuid=utils.generate_uuid(),
                name=str(idx), description='SE_{0}'.format(idx))
        response = self.get_json('/scoring_engines/?limit=2')
        self.assertEqual(2, len(response['scoring_engines']))

    def test_scoring_engines_collection_links_default_limit(self):
        for idx in range(1, 6):
            obj_utils.create_test_scoring_engine(
                self.context, id=idx, uuid=utils.generate_uuid(),
                name=str(idx), description='SE_{0}'.format(idx))
        cfg.CONF.set_override('max_limit', 3, 'api')
        response = self.get_json('/scoring_engines')
        self.assertEqual(3, len(response['scoring_engines']))

    def test_many_with_sort_key_uuid(self):
        scoring_engine_list = []
        for idx in range(1, 6):
            scoring_engine = obj_utils.create_test_scoring_engine(
                self.context, id=idx, uuid=utils.generate_uuid(),
                name=str(idx), description='SE_{0}'.format(idx))
            scoring_engine_list.append(scoring_engine.uuid)

        response = self.get_json('/scoring_engines/?sort_key=uuid')

        self.assertEqual(5, len(response['scoring_engines']))
        uuids = [s['uuid'] for s in response['scoring_engines']]
        self.assertEqual(sorted(scoring_engine_list), uuids)

    def test_sort_key_validation(self):
        response = self.get_json(
            '/goals?sort_key=%s' % 'bad_name',
            expect_errors=True)
        self.assertEqual(400, response.status_int)


class TestScoringEnginePolicyEnforcement(api_base.FunctionalTest):

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
            "scoring_engine:get_all", self.get_json, '/scoring_engines',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        se = obj_utils.create_test_scoring_engine(self.context)
        self._common_policy_check(
            "scoring_engine:get", self.get_json,
            '/scoring_engines/%s' % se.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "scoring_engine:detail", self.get_json,
            '/scoring_engines/detail',
            expect_errors=True)


class TestScoringEnginePolicyEnforcementWithAdminContext(
        TestListScoringEngine, api_base.AdminRoleTest):

    def setUp(self):
        super(TestScoringEnginePolicyEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "scoring_engine:detail": "rule:default",
            "scoring_engine:get": "rule:default",
            "scoring_engine:get_all": "rule:default"})
