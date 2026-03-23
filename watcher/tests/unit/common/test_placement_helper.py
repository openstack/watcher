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

from keystoneauth1 import loading as ka_loading
from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from watcher.common import placement_helper
from watcher.tests.fixtures import fakes as fake_requests
from watcher.tests.unit import base


CONF = cfg.CONF


class TestInventory(base.TestCase):
    def setUp(self):
        super().setUp()
        self.inventory_dict = {
            'total': 8,
            'reserved': 0,
            'min_unit': 1,
            'max_unit': 8,
            'step_size': 1,
            'allocation_ratio': 16.0,
        }

    def test_from_placement_api(self):
        inv = placement_helper.Inventory.from_placement_api(
            self.inventory_dict
        )
        self.assertEqual(8, inv.total)
        self.assertEqual(0, inv.reserved)
        self.assertEqual(1, inv.min_unit)
        self.assertEqual(8, inv.max_unit)
        self.assertEqual(1, inv.step_size)
        self.assertEqual(16.0, inv.allocation_ratio)

    def test_frozen(self):
        inv = placement_helper.Inventory.from_placement_api(
            self.inventory_dict
        )
        self.assertRaises(AttributeError, setattr, inv, 'total', 99)

    def test_equality(self):
        inv1 = placement_helper.Inventory.from_placement_api(
            self.inventory_dict
        )
        inv2 = placement_helper.Inventory(
            total=8,
            reserved=0,
            min_unit=1,
            max_unit=8,
            step_size=1,
            allocation_ratio=16.0,
        )
        self.assertEqual(inv1, inv2)


@mock.patch('keystoneauth1.session.Session.request')
class TestPlacementHelper(base.TestCase):
    def setUp(self):
        super().setUp()
        _AUTH_CONF_GROUP = 'watcher_clients_auth'
        ka_loading.register_auth_conf_options(CONF, _AUTH_CONF_GROUP)
        ka_loading.register_session_conf_options(CONF, _AUTH_CONF_GROUP)
        self.client = placement_helper.PlacementHelper()
        self.fake_err_msg = {
            'errors': [{'detail': 'The resource could not be found.'}]
        }

    def _add_default_kwargs(self, kwargs):
        kwargs['endpoint_filter'] = {
            'service_type': 'placement',
            'interface': CONF.placement_client.interface,
        }
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

    def test_get_inventories_OK(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()

        fake_inventories = {
            "DISK_GB": {
                "allocation_ratio": 1.0,
                "max_unit": 35,
                "min_unit": 1,
                "reserved": 0,
                "step_size": 1,
                "total": 35,
            },
            "MEMORY_MB": {
                "allocation_ratio": 1.5,
                "max_unit": 5825,
                "min_unit": 1,
                "reserved": 512,
                "step_size": 1,
                "total": 5825,
            },
            "VCPU": {
                "allocation_ratio": 16.0,
                "max_unit": 4,
                "min_unit": 1,
                "reserved": 0,
                "step_size": 1,
                "total": 4,
            },
        }
        mock_json_data = {
            'inventories': fake_inventories,
            "resource_provider_generation": 7,
        }

        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.OK, content=jsonutils.dump_as_bytes(mock_json_data)
        )

        result = self.client.get_inventories(rp_uuid)

        expected_url = f'/resource_providers/{rp_uuid}/inventories'
        self._assert_keystone_called_once(kss_req, expected_url, 'GET')
        expected = {
            rc: placement_helper.Inventory.from_placement_api(inv)
            for rc, inv in fake_inventories.items()
        }
        self.assertEqual(expected, result)

    def test_get_inventories_fail(self, kss_req):
        rp_uuid = uuidutils.generate_uuid()
        kss_req.return_value = fake_requests.FakeResponse(
            HTTPStatus.NOT_FOUND,
            content=jsonutils.dump_as_bytes(self.fake_err_msg),
        )
        result = self.client.get_inventories(rp_uuid)
        self.assertIsNone(result)
