# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from http import HTTPStatus
from unittest import mock

from watcher.common import placement_helper
from watcher.tests import base
from watcher.tests import fakes as fake_requests

from keystoneauth1 import loading as ka_loading
from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

CONF = cfg.CONF


@mock.patch('keystoneauth1.session.Session.request')
class TestPlacementHelper(base.TestCase):
    def setUp(self):
        super(TestPlacementHelper, self).setUp()
        _AUTH_CONF_GROUP = 'watcher_clients_auth'
        ka_loading.register_auth_conf_options(CONF, _AUTH_CONF_GROUP)
        ka_loading.register_session_conf_options(CONF, _AUTH_CONF_GROUP)
        self.client = placement_helper.PlacementHelper()
        self.fake_err_msg = {
            'errors': [{
                'detail': 'The resource could not be found.',
            }]
        }

    def _add_default_kwargs(self, kwargs):
        kwargs['endpoint_filter'] = {
            'service_type': 'placement',
            'interface': CONF.placement_client.interface}
        kwargs['headers'] = {'accept': 'application/json'}
        kwargs['microversion'] = CONF.placement_client.api_version
        kwargs['raise_exc'] = False

    def _assert_keystone_called_once(self, kss_req, url, method, **kwargs):
        self._add_default_kwargs(kwargs)
        # request method has added param rate_semaphore since Stein cycle
        if 'rate_semaphore' in kss_req.call_args[1]:
            kwargs['rate_semaphore'] = mock.ANY
        kss_req.assert_called_once_with(url, method, **kwargs)

    def test_get(self, kss_req):
        kss_req.return_value = fake_requests.FakeResponse(HTTPStatus.OK)
        url = '/resource_providers'
        resp = self.client.get(url)
        self.assertEqual(HTTPStatus.OK, resp.status_code)
        self._assert_keystone_called_once(kss_req, url, 'GET')

    def test_get_resource_providers_OK(self, kss_req):
        rp_name = 'compute'
        rp_uuid = uuidutils.generate_uuid()
        parent_uuid = uuidutils.generate_uuid()

        fake_rp = [{'uuid': rp_uuid,
                    'name': rp_name,
                    'generation': 0,
                    'parent_provider_uuid': parent_uuid}]

        mock_json_data = {
            'resource_providers': fake_rp
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data))

        result = self.client.get_resource_providers(rp_name)

        expected_url = '/resource_providers?name=compute'
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        self.assertEqual(fake_rp, result)

    def test_get_resource_providers_no_rp_OK(self, kss_req):
        rp_name = None
        rp_uuid = uuidutils.generate_uuid()
        parent_uuid = uuidutils.generate_uuid()

        fake_rp = [{'uuid': rp_uuid,
                    'name': 'compute',
                    'generation': 0,
                    'parent_provider_uuid': parent_uuid}]

        mock_json_data = {
            'resource_providers': fake_rp
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data))

        result = self.client.get_resource_providers(rp_name)

        expected_url = '/resource_providers'
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        self.assertEqual(fake_rp, result)

    def test_get_resource_providers_fail(self, kss_req):
        rp_name = 'compute'
        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.BAD_REQUEST,
            content=jsonutils.dump_as_bytes(self.fake_err_msg))
        result = self.client.get_resource_providers(rp_name)
        self.assertIsNone(result)

    def test_get_inventories_OK(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()

        fake_inventories = {
            "DISK_GB": {
                "allocation_ratio": 1.0,
                "max_unit": 35,
                "min_unit": 1,
                "reserved": 0,
                "step_size": 1,
                "total": 35
            },
            "MEMORY_MB": {
                "allocation_ratio": 1.5,
                "max_unit": 5825,
                "min_unit": 1,
                "reserved": 512,
                "step_size": 1,
                "total": 5825
            },
            "VCPU": {
                "allocation_ratio": 16.0,
                "max_unit": 4,
                "min_unit": 1,
                "reserved": 0,
                "step_size": 1,
                "total": 4
            },
        }
        mock_json_data = {
            'inventories': fake_inventories,
            "resource_provider_generation": 7
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data))

        result = self.client.get_inventories(rp_uuid)

        expected_url = '/resource_providers/%s/inventories' % rp_uuid
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        self.assertEqual(fake_inventories, result)

    def test_get_inventories_fail(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()
        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.NOT_FOUND,
            content=jsonutils.dump_as_bytes(self.fake_err_msg))
        result = self.client.get_inventories(rp_uuid)
        self.assertIsNone(result)

    def test_get_provider_traits_OK(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()

        fake_traits = ["CUSTOM_HW_FPGA_CLASS1",
                       "CUSTOM_HW_FPGA_CLASS3"]
        mock_json_data = {
            'traits': fake_traits,
            "resource_provider_generation": 7
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data))

        result = self.client.get_provider_traits(rp_uuid)

        expected_url = '/resource_providers/%s/traits' % rp_uuid
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        self.assertEqual(fake_traits, result)

    def test_get_provider_traits_fail(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()
        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.NOT_FOUND,
            content=jsonutils.dump_as_bytes(self.fake_err_msg))
        result = self.client.get_provider_traits(rp_uuid)
        self.assertIsNone(result)

    def test_get_allocations_for_consumer_OK(self, kss_req):
        c_uuid = uuidutils.generate_uuid()

        fake_allocations = {
            "92637880-2d79-43c6-afab-d860886c6391": {
                "generation": 2,
                "resources": {
                    "DISK_GB": 5
                }
            },
            "ba8e1ef8-7fa3-41a4-9bb4-d7cb2019899b": {
                "generation": 8,
                "resources": {
                    "MEMORY_MB": 512,
                    "VCPU": 2
                }
            }
        }
        mock_json_data = {
            'allocations': fake_allocations,
            "consumer_generation": 1,
            "project_id": "7e67cbf7-7c38-4a32-b85b-0739c690991a",
            "user_id": "067f691e-725a-451a-83e2-5c3d13e1dffc"
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data))

        result = self.client.get_allocations_for_consumer(c_uuid)

        expected_url = '/allocations/%s' % c_uuid
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        self.assertEqual(fake_allocations, result)

    def test_get_allocations_for_consumer_fail(self, kss_req):
        c_uuid = uuidutils.generate_uuid()
        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.NOT_FOUND,
            content=jsonutils.dump_as_bytes(self.fake_err_msg))
        result = self.client.get_allocations_for_consumer(c_uuid)
        self.assertIsNone(result)

    def test_get_usages_for_resource_provider_OK(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()

        fake_usages = {
            "DISK_GB": 1,
            "MEMORY_MB": 512,
            "VCPU": 1
        }
        mock_json_data = {
            'usages': fake_usages,
            "resource_provider_generation": 7
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data))

        result = self.client.get_usages_for_resource_provider(rp_uuid)

        expected_url = '/resource_providers/%s/usages' % rp_uuid
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        self.assertEqual(fake_usages, result)

    def test_get_usages_for_resource_provider_fail(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()
        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.NOT_FOUND,
            content=jsonutils.dump_as_bytes(self.fake_err_msg))
        result = self.client.get_usages_for_resource_provider(rp_uuid)
        self.assertIsNone(result)

    def test_get_candidate_providers_OK(self, kss_req):
        resources = 'VCPU:4,DISK_GB:64,MEMORY_MB:2048'

        fake_provider_summaries = {
            "a99bad54-a275-4c4f-a8a3-ac00d57e5c64": {
                "resources": {
                    "DISK_GB": {
                        "used": 0,
                        "capacity": 1900
                    },
                },
                "traits": ["MISC_SHARES_VIA_AGGREGATE"],
                "parent_provider_uuid": None,
                "root_provider_uuid": "a99bad54-a275-4c4f-a8a3-ac00d57e5c64"
            },
            "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                "resources": {
                    "VCPU": {
                        "used": 0,
                        "capacity": 384
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 196608
                    },
                },
                "traits": ["HW_CPU_X86_SSE2", "HW_CPU_X86_AVX2"],
                "parent_provider_uuid": None,
                "root_provider_uuid": "35791f28-fb45-4717-9ea9-435b3ef7c3b3"
            },
        }
        mock_json_data = {
            'provider_summaries': fake_provider_summaries,
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data))

        result = self.client.get_candidate_providers(resources)

        expected_url = "/allocation_candidates?%s" % resources
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        self.assertEqual(fake_provider_summaries, result)

    def test_get_candidate_providers_fail(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()
        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.NOT_FOUND,
            content=jsonutils.dump_as_bytes(self.fake_err_msg))
        result = self.client.get_candidate_providers(rp_uuid)
        self.assertIsNone(result)
