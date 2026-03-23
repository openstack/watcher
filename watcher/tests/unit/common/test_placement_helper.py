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

import fixtures

from openstack import exceptions as sdk_exc
from oslo_utils import uuidutils

from watcher.common import placement_helper
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils


class TestInventory(test_utils.PlacementResourcesMixin, base.TestCase):
    def setUp(self):
        super().setUp()
        self.inventory = self.create_openstacksdk_inventory(
            total=8,
            reserved=0,
            min_unit=1,
            max_unit=8,
            step_size=1,
            allocation_ratio=16.0,
        )

    def test_from_openstacksdk(self):
        inv = placement_helper.Inventory.from_openstacksdk(self.inventory)
        self.assertEqual(8, inv.total)
        self.assertEqual(0, inv.reserved)
        self.assertEqual(1, inv.min_unit)
        self.assertEqual(8, inv.max_unit)
        self.assertEqual(1, inv.step_size)
        self.assertEqual(16.0, inv.allocation_ratio)

    def test_frozen(self):
        inv = placement_helper.Inventory.from_openstacksdk(self.inventory)
        self.assertRaises(AttributeError, setattr, inv, 'total', 99)

    def test_equality(self):
        inv1 = placement_helper.Inventory.from_openstacksdk(self.inventory)
        inv2 = placement_helper.Inventory(
            total=8,
            reserved=0,
            min_unit=1,
            max_unit=8,
            step_size=1,
            allocation_ratio=16.0,
        )
        self.assertEqual(inv1, inv2)


class TestPlacementHelper(test_utils.PlacementResourcesMixin, base.TestCase):
    def setUp(self):
        super().setUp()
        self.mock_conn = self.useFixture(
            fixtures.MockPatch("watcher.common.clients.get_sdk_connection")
        ).mock.return_value
        self.client = placement_helper.PlacementHelper()

    def test_get_inventories_OK(self):
        rp_uuid = uuidutils.generate_uuid()

        fake_inventories = {
            "DISK_GB": self.create_openstacksdk_inventory(
                resource_class="DISK_GB",
                allocation_ratio=1.0,
                max_unit=35,
                min_unit=1,
                reserved=0,
                step_size=1,
                total=35,
            ),
            "MEMORY_MB": self.create_openstacksdk_inventory(
                resource_class="MEMORY_MB",
                allocation_ratio=1.5,
                max_unit=5825,
                min_unit=1,
                reserved=512,
                step_size=1,
                total=5825,
            ),
            "VCPU": self.create_openstacksdk_inventory(
                resource_class="VCPU",
                allocation_ratio=16.0,
                max_unit=4,
                min_unit=1,
                reserved=0,
                step_size=1,
                total=4,
            ),
        }
        placement = self.mock_conn.placement.resource_provider_inventories
        placement.return_value = list(fake_inventories.values())

        result = self.client.get_inventories(rp_uuid)

        expected = {
            rc: placement_helper.Inventory.from_openstacksdk(inv)
            for rc, inv in fake_inventories.items()
        }
        self.assertEqual(expected, result)

    def test_get_inventories_fail(self):
        rp_uuid = uuidutils.generate_uuid()
        placement = self.mock_conn.placement.resource_provider_inventories
        placement.side_effect = sdk_exc.NotFoundException()
        self.assertIsNone(self.client.get_inventories(rp_uuid))

    def test_get_inventories_fail_http_error(self):
        rp_uuid = uuidutils.generate_uuid()
        placement = self.mock_conn.placement.resource_provider_inventories
        placement.side_effect = sdk_exc.HttpException()
        self.assertIsNone(self.client.get_inventories(rp_uuid))
