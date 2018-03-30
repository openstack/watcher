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
from six.moves.urllib import parse as urlparse

from watcher.tests.api import base as api_base
from watcher.tests.objects import utils as obj_utils


class TestListService(api_base.FunctionalTest):

    def _assert_service_fields(self, service):
        service_fields = ['id', 'name', 'host', 'status']
        for field in service_fields:
            self.assertIn(field, service)

    def test_one(self):
        service = obj_utils.create_test_service(self.context)
        response = self.get_json('/services')
        self.assertEqual(service.id, response['services'][0]["id"])
        self._assert_service_fields(response['services'][0])

    def test_get_one_by_id(self):
        service = obj_utils.create_test_service(self.context)
        response = self.get_json('/services/%s' % service.id)
        self.assertEqual(service.id, response["id"])
        self.assertEqual(service.name, response["name"])
        self._assert_service_fields(response)

    def test_get_one_by_name(self):
        service = obj_utils.create_test_service(self.context)
        response = self.get_json(urlparse.quote(
            '/services/%s' % service['name']))
        self.assertEqual(service.id, response['id'])
        self._assert_service_fields(response)

    def test_get_one_soft_deleted(self):
        service = obj_utils.create_test_service(self.context)
        service.soft_delete()
        response = self.get_json(
            '/services/%s' % service['id'],
            headers={'X-Show-Deleted': 'True'})
        self.assertEqual(service.id, response['id'])
        self._assert_service_fields(response)

        response = self.get_json(
            '/services/%s' % service['id'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_detail(self):
        service = obj_utils.create_test_service(self.context)
        response = self.get_json('/services/detail')
        self.assertEqual(service.id, response['services'][0]["id"])
        self._assert_service_fields(response['services'][0])
        for service in response['services']:
            self.assertTrue(
                all(val is not None for key, val in service.items()
                    if key in ['id', 'name', 'host', 'status'])
            )

    def test_detail_against_single(self):
        service = obj_utils.create_test_service(self.context)
        response = self.get_json('/services/%s/detail' % service.id,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        service_list = []
        for idx in range(1, 4):
            service = obj_utils.create_test_service(
                self.context, id=idx, host='CONTROLLER1',
                name='SERVICE_{0}'.format(idx))
            service_list.append(service.id)
        for idx in range(1, 4):
            service = obj_utils.create_test_service(
                self.context, id=3+idx, host='CONTROLLER2',
                name='SERVICE_{0}'.format(idx))
            service_list.append(service.id)
        response = self.get_json('/services')
        self.assertEqual(6, len(response['services']))
        for service in response['services']:
            self.assertTrue(
                all(val is not None for key, val in service.items()
                    if key in ['id', 'name', 'host', 'status']))

    def test_many_without_soft_deleted(self):
        service_list = []
        for id_ in [1, 2, 3]:
            service = obj_utils.create_test_service(
                self.context, id=id_, host='CONTROLLER',
                name='SERVICE_{0}'.format(id_))
            service_list.append(service.id)
        for id_ in [4, 5]:
            service = obj_utils.create_test_service(
                self.context, id=id_, host='CONTROLLER',
                name='SERVICE_{0}'.format(id_))
            service.soft_delete()
        response = self.get_json('/services')
        self.assertEqual(3, len(response['services']))
        ids = [s['id'] for s in response['services']]
        self.assertEqual(sorted(service_list), sorted(ids))

    def test_services_collection_links(self):
        for idx in range(1, 6):
            obj_utils.create_test_service(
                self.context, id=idx,
                host='CONTROLLER',
                name='SERVICE_{0}'.format(idx))
        response = self.get_json('/services/?limit=2')
        self.assertEqual(2, len(response['services']))

    def test_services_collection_links_default_limit(self):
        for idx in range(1, 6):
            obj_utils.create_test_service(
                self.context, id=idx,
                host='CONTROLLER',
                name='SERVICE_{0}'.format(idx))
        cfg.CONF.set_override('max_limit', 3, 'api')
        response = self.get_json('/services')
        self.assertEqual(3, len(response['services']))

    def test_many_with_sort_key_name(self):
        service_list = []
        for id_ in range(1, 4):
            service = obj_utils.create_test_service(
                self.context, id=id_, host='CONTROLLER',
                name='SERVICE_{0}'.format(id_))
            service_list.append(service.name)

        response = self.get_json('/services/?sort_key=name')

        self.assertEqual(3, len(response['services']))
        names = [s['name'] for s in response['services']]
        self.assertEqual(sorted(service_list), names)

    def test_sort_key_validation(self):
        response = self.get_json(
            '/services?sort_key=%s' % 'bad_name',
            expect_errors=True)
        self.assertEqual(400, response.status_int)


class TestServicePolicyEnforcement(api_base.FunctionalTest):

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
            "service:get_all", self.get_json, '/services',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        service = obj_utils.create_test_service(self.context)
        self._common_policy_check(
            "service:get", self.get_json,
            '/services/%s' % service.id,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "service:detail", self.get_json,
            '/services/detail',
            expect_errors=True)


class TestServiceEnforcementWithAdminContext(TestListService,
                                             api_base.AdminRoleTest):

    def setUp(self):
        super(TestServiceEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "service:detail": "rule:default",
            "service:get": "rule:default",
            "service:get_all": "rule:default"})
