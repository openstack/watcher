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

from http import HTTPStatus

from watcher.api.controllers.v1 import versions
from watcher.tests.api import base as api_base


SERVICE_TYPE = 'infra-optim'
H_MIN_VER = 'openstack-api-minimum-version'
H_MAX_VER = 'openstack-api-maximum-version'
H_RESP_VER = 'openstack-api-version'
MIN_VER = versions.min_version_string()
MAX_VER = versions.max_version_string()


class TestMicroversions(api_base.FunctionalTest):

    controller_list_response = [
        'scoring_engines', 'audit_templates', 'audits', 'actions',
        'action_plans', 'services']

    def setUp(self):
        super(TestMicroversions, self).setUp()

    def test_wrong_major_version(self):
        response = self.get_json(
            '/',
            headers={'OpenStack-API-Version': ' '.join([SERVICE_TYPE,
                                                        '10'])},
            expect_errors=True, return_json=False)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(HTTPStatus.NOT_ACCEPTABLE, response.status_int)
        expected_error_msg = ('Invalid value for'
                              ' OpenStack-API-Version header')
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])

    def test_extend_initial_version_with_micro(self):
        response = self.get_json(
            '/',
            headers={'OpenStack-API-Version': ' '.join([SERVICE_TYPE,
                                                        '1'])},
            return_json=False)
        self.assertEqual(response.headers[H_MIN_VER], MIN_VER)
        self.assertEqual(response.headers[H_MAX_VER], MAX_VER)
        self.assertEqual(response.headers[H_RESP_VER],
                         ' '.join([SERVICE_TYPE, MIN_VER]))
        self.assertTrue(all(x in response.json.keys() for x in
                            self.controller_list_response))

    def test_without_microversion(self):
        response = self.get_json('/', return_json=False)
        self.assertEqual(response.headers[H_MIN_VER], MIN_VER)
        self.assertEqual(response.headers[H_MAX_VER], MAX_VER)
        self.assertEqual(response.headers[H_RESP_VER],
                         ' '.join([SERVICE_TYPE, MIN_VER]))
        self.assertTrue(all(x in response.json.keys() for x in
                            self.controller_list_response))

    def test_new_client_new_api(self):
        response = self.get_json(
            '/',
            headers={'OpenStack-API-Version': ' '.join([SERVICE_TYPE,
                                                        '1.1'])},
            return_json=False)
        self.assertEqual(response.headers[H_MIN_VER], MIN_VER)
        self.assertEqual(response.headers[H_MAX_VER], MAX_VER)
        self.assertEqual(response.headers[H_RESP_VER],
                         ' '.join([SERVICE_TYPE, '1.1']))
        self.assertTrue(all(x in response.json.keys() for x in
                            self.controller_list_response))

    def test_latest_microversion(self):
        response = self.get_json(
            '/',
            headers={'OpenStack-API-Version': ' '.join([SERVICE_TYPE,
                                                        'latest'])},
            return_json=False)
        self.assertEqual(response.headers[H_MIN_VER], MIN_VER)
        self.assertEqual(response.headers[H_MAX_VER], MAX_VER)
        self.assertEqual(response.headers[H_RESP_VER],
                         ' '.join([SERVICE_TYPE, MAX_VER]))
        self.assertTrue(all(x in response.json.keys() for x in
                            self.controller_list_response))

    def test_unsupported_version(self):
        response = self.get_json(
            '/',
            headers={'OpenStack-API-Version': ' '.join([SERVICE_TYPE,
                                                        '1.999'])},
            expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_ACCEPTABLE, response.status_int)
        self.assertEqual(response.headers[H_MIN_VER], MIN_VER)
        self.assertEqual(response.headers[H_MAX_VER], MAX_VER)
        expected_error_msg = ('Version 1.999 was requested but the minor '
                              'version is not supported by this service. '
                              'The supported version range is')
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])
