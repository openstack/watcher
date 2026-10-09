# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Functional tests for the Cinder storage data model emulator.

Validates that storage topology loaded from XML scenario files
populates the Cinder API emulator correctly.
"""

import os

from watcher.tests.functional import base
from watcher.tests.functional import topology


class TestCinderModelFromXML(base.WatcherFunctionalTestCase):
    """Validate loading storage topology from XML model files."""

    STORAGE_TOPOLOGY = topology.StorageTopology()

    XML_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '../unit/decision_engine/model/data/storage_scenario_1.xml',
    )

    def setUp(self):
        super().setUp()
        self.emulator = self.cinder_fixture.cinder_emulator
        self.emulator.load_from_xml(self.XML_PATH)

    def test_storage_node_count(self):
        self.assertEqual(2, len(self.emulator.services))

    def test_storage_node_hosts(self):
        self.assertEqual(
            {'host_0@backend_0', 'host_1@backend_1'},
            set(self.emulator.services),
        )

    def test_storage_node_attributes(self):
        node = self.emulator.services['host_0@backend_0']
        self.assertEqual('zone_0', node['zone'])
        self.assertEqual('enabled', node['status'])
        self.assertEqual('up', node['state'])
        self.assertEqual('cinder-volume', node['binary'])

    def test_pool_count(self):
        self.assertEqual(4, len(self.emulator.pools))

    def test_pool_names(self):
        self.assertEqual(
            {
                'host_0@backend_0#pool_0',
                'host_0@backend_0#pool_1',
                'host_1@backend_1#pool_0',
                'host_1@backend_1#pool_1',
            },
            set(self.emulator.pools),
        )

    def test_pool_attributes(self):
        pool = self.emulator.pools['host_0@backend_0#pool_0']
        caps = pool['capabilities']
        self.assertEqual(500.0, caps['total_capacity_gb'])
        self.assertEqual(420.0, caps['free_capacity_gb'])
        self.assertEqual(80.0, caps['provisioned_capacity_gb'])
        self.assertEqual(80.0, caps['allocated_capacity_gb'])
        self.assertEqual(2, caps['total_volumes'])
        self.assertEqual('backend_0', caps['volume_backend_name'])

    def test_volume_count(self):
        # 8 nested under pools + 1 orphan at ModelRoot
        self.assertEqual(9, len(self.emulator.volumes))

    def test_nested_volume_attributes(self):
        vol_id = '5028b1eb-8749-48ae-a42c-5bdd1323976f'
        vol = self.emulator.volumes[vol_id]
        self.assertEqual('name_0', vol['name'])
        self.assertEqual(40, vol['size'])
        self.assertEqual('in-use', vol['status'])
        self.assertEqual('type_0', vol['volume_type'])
        self.assertEqual(
            'host_0@backend_0#pool_0', vol['os-vol-host-attr:host']
        )
        self.assertEqual(
            '91FFFE30-78A0-4152-ACD2-8310FF274DC9',
            vol['os-vol-tenant-attr:tenant_id'],
        )
        self.assertFalse(vol['bootable'])
        self.assertTrue(vol['multiattach'])
        self.assertIsNone(vol['snapshot_id'])
        self.assertEqual(
            [{'server_id': 'server', 'attachment_id': 'attachment'}],
            vol['attachments'],
        )
        self.assertEqual(
            {'readonly': False, 'attached_mode': 'rw'}, vol['metadata']
        )

    def test_orphan_volume(self):
        vol_id = '4d1c952d-95d0-4aac-82aa-c3cb509af9f3'
        vol = self.emulator.volumes[vol_id]
        self.assertEqual('name_8', vol['name'])
        self.assertEqual('type_1', vol['volume_type'])
        self.assertEqual(
            'host_1@backend_1#pool_1', vol['os-vol-host-attr:host']
        )

    def test_volume_types_synthesized(self):
        type_names = {vt['name'] for vt in self.emulator.volume_types.values()}
        self.assertEqual({'type_0', 'type_1'}, type_names)
