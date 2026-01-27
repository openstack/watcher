# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import fixtures
from unittest import mock

import cinderclient

from watcher.common import nova_helper
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.unit.common import utils as test_utils
from watcher.tests.unit.decision_engine.model import faker_cluster_state
from watcher.tests.unit.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy

volume_uuid_mapping = faker_cluster_state.volume_uuid_mapping


class TestZoneMigration(test_utils.NovaResourcesMixin, TestBaseStrategy):

    def setUp(self):
        super().setUp()

        # fake storage cluster
        self.fake_s_cluster = faker_cluster_state.FakerStorageModelCollector()

        p_s_model = mock.patch.object(
            strategies.ZoneMigration, "storage_model",
            new_callable=mock.PropertyMock)
        self.m_s_model = p_s_model.start()
        self.addCleanup(p_s_model.stop)

        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model

        model = self.fake_s_cluster.generate_scenario_1()
        self.m_s_model.return_value = model

        self.input_parameters = {
            "storage_pools": [
                {"src_pool": "src1@back1#pool1",
                 "dst_pool": "dst1@back1#pool1",
                 "src_type": "type1", "dst_type": "type1"},
                {"src_pool": "src2@back1#pool1",
                 "dst_pool": "dst2@back2#pool1",
                 "src_type": "type2", "dst_type": "type3"}
            ],
            "compute_nodes": [
                {"src_node": "src1", "dst_node": "dst1"},
                {"src_node": "src2", "dst_node": "dst2"}
            ],
            "parallel_per_node": 2,
            "parallel_per_pool": 2,
            "parallel_total": 6,
            "with_attached_volume": False
        }

        self.strategy = strategies.ZoneMigration(
            config=mock.Mock())
        self.strategy.input_parameters = self.input_parameters

        self.m_osc = self.useFixture(
            fixtures.MockPatch(
                "watcher.common.clients.OpenStackClients",
                autospec=True)).mock.return_value

        self.m_n_helper = self.useFixture(
            fixtures.MockPatch(
                "watcher.common.nova_helper.NovaHelper",
                autospec=False)).mock.return_value

        self.m_c_helper = self.useFixture(
            fixtures.MockPatch(
                "watcher.common.cinder_helper.CinderHelper",
                autospec=False)).mock.return_value

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock(spec=cinderclient.v3.volumes.Volume)
        volume.id = kwargs.get('id', utils.generate_uuid())
        volume.name = kwargs.get('name', 'fake_name')
        volume.status = kwargs.get('status', 'available')
        tenant_id = kwargs.get('project_id', None)
        setattr(volume, 'os-vol-tenant-attr:tenant_id', tenant_id)
        setattr(volume, 'os-vol-host-attr:host', kwargs.get('host'))
        setattr(volume, 'size', kwargs.get('size', '1'))
        setattr(volume, 'created_at',
                kwargs.get('created_at', '1977-01-01T00:00:00'))
        setattr(volume, 'attachments', kwargs.get('attachments', []))
        volume.volume_type = kwargs.get('volume_type', 'type1')

        return volume

    @staticmethod
    def fake_flavor(**kwargs):
        flavor = mock.MagicMock()
        flavor.id = kwargs.get('id', None)
        flavor.ram = kwargs.get('mem_size', '1')
        flavor.vcpus = kwargs.get('vcpu_num', '1')
        flavor.disk = kwargs.get('disk_size', '1')

        return flavor

    def test_get_src_node_list(self):
        instances = self.strategy.get_src_node_list()
        self.assertEqual(sorted(instances), sorted(["src1", "src2"]))

    def test_get_instances(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src3",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        instances = self.strategy.get_instances()

        # src1,src2 is in instances
        # src3 is not in instances
        self.assertIn(instance_on_src1, instances)
        self.assertIn(instance_on_src2, instances)
        self.assertNotIn(instance_on_src3, instances)

    def test_get_instances_with_instance_not_found(self):
        # Create a test instance without a known id
        # so we expect it to not be in the model
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d8f0ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )

        # Mock nova helper to return our test instance
        self.m_n_helper.get_instance_list.return_value = [instance_on_src1]

        # Verify that the instance does not exist in the model
        instances = self.strategy.get_instances()
        self.assertEqual([], instances)

    def test_get_volumes_with_volume_not_found(self):
        # Create a test volume without an known id
        # so we expect it to not be in the model
        volume_on_src1 = self.fake_volume(
            host="src1@back1#pool1",
            name="volume_1")

        # Mock cinder helper to return our tets volume
        self.m_c_helper.get_volume_list.return_value = [volume_on_src1]

        # Call get_volumes and verify the volume does not exist in the model
        volumes = self.strategy.get_volumes()
        self.assertEqual([], volumes)

    def test_get_volumes(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src3@back2#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
        ]

        volumes = self.strategy.get_volumes()

        # src1 is in instances
        # src2,src3 is not in instances
        self.assertIn(volume_on_src1, volumes)
        self.assertNotIn(volume_on_src2, volumes)
        self.assertNotIn(volume_on_src3, volumes)

    def test_get_volumes_no_src_type(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src3@back2#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
        ]
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "dst_type": "type1"},
            {"src_pool": "src2@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "dst_type": "type3"}
        ]

        volumes = self.strategy.get_volumes()

        # src1, src2 are in volumes
        # src3 is not in volumes
        self.assertIn(volume_on_src1, volumes)
        self.assertIn(volume_on_src2, volumes)
        self.assertNotIn(volume_on_src3, volumes)

    def test_get_volumes_different_types_different_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          volume_type="type2",
                                          name="volume_0")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4,
        ]

        volumes = self.strategy.get_volumes()

        self.m_c_helper.get_volume_list.assert_called_once_with()

        # src1 is in volumes since it has volume type "type1" and host
        # "src1@back1#pool1" which matches the default input parameters
        # for storage_pools
        # src4 is in volumes since it has volume type "type2" and host
        # "src2@back1#pool1" which matches the default input parameters
        # for storage_pools
        # src2 is not in volumes since it has volume type "type2" and host
        # "src2@back1#pool1" which does not match the default input parameters
        # for storage_pools
        # src3 is not in volumes since it has volume type "type1" and host
        # "src2@back1#pool1" which does not match the default input parameters
        # for storage_pools
        self.assertIn(volume_on_src1, volumes)
        self.assertIn(volume_on_src4, volumes)
        self.assertNotIn(volume_on_src3, volumes)
        self.assertNotIn(volume_on_src2, volumes)

    def test_get_volumes_different_types_same_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_0"],
                                          volume_type="type3",
                                          name="volume_0")
        self.m_c_helper.get_volume_list.return_value = {
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4,
        }

        volumes = self.strategy.get_volumes()

        self.m_c_helper.get_volume_list.assert_called_once_with()

        # src1 is in volumes since it has volume type "type1" and host
        # "src1@back1#pool1" which
        # matches the default input parameters for storage_pools
        # src3 is in volumes since it has volume type "type1" and host
        # "src1@back1#pool1" which
        # matches the default input parameters for storage_pools
        # src2 is not in volumes since it has volume type "type2" and host
        # "src1@back1#pool1" which
        # does not match the default input parameters for storage_pools
        # src4 is not in volumes since it has volume type "type3" which
        # does not match the default input parameters for storage_pools
        self.assertIn(volume_on_src1, volumes)
        self.assertIn(volume_on_src3, volumes)
        self.assertNotIn(volume_on_src4, volumes)
        self.assertNotIn(volume_on_src2, volumes)

    def test_get_volumes_all_types_in_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_0"],
                                          volume_type="type2",
                                          name="volume_4")
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "src_type": "type2", "dst_type": "type3"}
        ]
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4,
        ]

        volumes = self.strategy.get_volumes()

        self.m_c_helper.get_volume_list.assert_called_once_with()

        # all volumes are selected since they match the src_pool and src_type
        # in the input parameters
        self.assertIn(volume_on_src1, volumes)
        self.assertIn(volume_on_src3, volumes)
        self.assertIn(volume_on_src4, volumes)
        self.assertIn(volume_on_src2, volumes)

    def test_get_volumes_type_in_all_pools(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_0"],
                                          name="volume_0")
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
            {"src_pool": "src2@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "src_type": "type1", "dst_type": "type3"}
        ]
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4,
        ]

        volumes = self.strategy.get_volumes()

        self.m_c_helper.get_volume_list.assert_called_once_with()

        # all volumes are selected since they match the src_pool and src_type
        # in the input parameters
        self.assertIn(volume_on_src1, volumes)
        self.assertIn(volume_on_src3, volumes)
        self.assertIn(volume_on_src4, volumes)
        self.assertIn(volume_on_src2, volumes)

    def test_get_volumes_select_no_volumes(self):
        volume_on_src1 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src3@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3
        ]

        volumes = self.strategy.get_volumes()

        self.m_c_helper.get_volume_list.assert_called_once_with()

        # no volumes are selected since none of the volumes match the src_pool
        # and src_type in the input parameters
        self.assertEqual(len(volumes), 0)

    def test_get_volumes_duplicated_input(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          volume_type="type2",
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_0"],
                                          name="volume_4")
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src2@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
            {"src_pool": "src2@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "src_type": "type1", "dst_type": "type3"}
        ]
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4,
        ]

        volumes = self.strategy.get_volumes()

        self.m_c_helper.get_volume_list.assert_called_once_with()

        # src4 is in volumes since it has volume type "type1" and host
        # "src2@back1#pool1" which matches the default input parameters for
        # storage_pools
        # src1, src2 are not in volumes since they are in host
        # "src1@back1#pool1" which does not match the test input parameters for
        # storage_pools
        # src3 is not in volumes since it has volume type "type2" which
        # does not match the test input parameters for storage_pools
        self.assertIn(volume_on_src4, volumes)
        self.assertNotIn(volume_on_src1, volumes)
        self.assertNotIn(volume_on_src2, volumes)
        self.assertNotIn(volume_on_src3, volumes)
        # only src4 is selected
        self.assertEqual(len(volumes), 1)

    # execute #

    def test_execute_live_migrate_instance(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("live", 0))
        global_efficacy_value = solution.global_efficacy[0].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_live_migrate_instance_no_dst_node(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
        ]
        self.m_c_helper.get_volume_list.return_value = []
        self.input_parameters["compute_nodes"] = [{"src_node": "src1"}]
        solution = self.strategy.execute()
        migration_params = solution.actions[0]['input_parameters']
        # since we have not passed 'dst_node' in the input, we should not have
        # a destination_node in the generated migration action
        self.assertNotIn('destination_node', migration_params)

    def test_execute_cold_migrate_instance(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "status": "SHUTOFF",
            "vm_state": "stopped",
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
        ]

        self.m_c_helper.get_volume_list.return_value = []
        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("cold", 0))
        global_efficacy_value = solution.global_efficacy[1].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volume(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("migrate", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volume_no_dst_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,

            ]
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
        ]
        self.m_n_helper.get_instance_list.return_value = []
        solution = self.strategy.execute()
        # check that there are no volume migrations proposed, because the input
        # parameters do not have a dst_pool and dst_type==src_type
        self.assertEqual(len(solution.actions), 0)

    def test_execute_migrate_volume_dst_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,

            ]
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1",
             "src_type": "type1",
             "dst_pool": "back2",
             "dst_type": "type1"},

            ]
        self.m_n_helper.get_instance_list.return_value = []
        solution = self.strategy.execute()
        # check that there is one volume migration proposed
        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("migrate", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volume_no_compute_nodes(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        vol_attach = [{"server_id": instance_on_src1.uuid}]
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
        ]
        self.m_n_helper.find_instance.return_value = instance_on_src1
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1",
                                          status="in-use",
                                          attachments=vol_attach)
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            ]
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1",
             "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
            ]
        self.input_parameters["compute_nodes"] = None
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
        ]
        self.input_parameters["with_attached_volume"] = True

        # check that the solution contains one volume migration and no
        # instance migration, once the bug is fixed
        solution = self.strategy.execute()
        self.assertEqual(len(solution.actions), 1)
        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions]
            )
        self.assertEqual(0, migration_types.get("live", 0))
        self.assertEqual(1, migration_types.get("migrate", 0))

    def test_execute_retype_volume(self):
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src2
        ]

        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("retype", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_swap_volume(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src1.status = "in-use"
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        # watcher no longer implements swap. it is now an
        # alias for migrate.
        self.assertEqual(0, migration_types.get("swap", 0))
        self.assertEqual(1, migration_types.get("migrate", 1))
        global_efficacy_value = solution.global_efficacy[3].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volumes_no_src_type(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src3@back2#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3
        ]
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "dst_type": "type1"},
            {"src_pool": "src2@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "dst_type": "type3"}
        ]
        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        self.assertEqual(2, len(solution.actions))
        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1,
                         migration_types.get("migrate", 0))
        self.assertEqual(1,
                         migration_types.get("retype", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volumes_different_types_different_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          volume_type="type2",
                                          name="volume_0")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4
        ]
        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        self.assertEqual(2, len(solution.actions))
        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1,
                         migration_types.get("migrate", 0))
        self.assertEqual(1,
                         migration_types.get("retype", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volumes_different_types_same_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_0"],
                                          volume_type="type3",
                                          name="volume_0")

        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4
        ]
        self.m_n_helper.get_instance_list.return_value = []
        solution = self.strategy.execute()

        self.assertEqual(2, len(solution.actions))
        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(2,
                         migration_types.get("migrate", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volumes_all_types_in_pool(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_0"],
                                          volume_type="type2",
                                          name="volume_4")
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "src_type": "type2", "dst_type": "type3"}
        ]
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4
        ]
        self.m_n_helper.get_instance_list.return_value = []
        solution = self.strategy.execute()

        self.assertEqual(2, len(solution.actions))
        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1,
                         migration_types.get("migrate", 0))
        self.assertEqual(1,
                         migration_types.get("retype", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(50, global_efficacy_value)

    def test_execute_migrate_volumes_type_in_all_pools(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        volume_on_src4 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_0"],
                                          name="volume_0")
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
            {"src_pool": "src2@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "src_type": "type1", "dst_type": "type3"}
        ]
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
            volume_on_src4
        ]
        self.m_n_helper.get_instance_list.return_value = []
        solution = self.strategy.execute()

        self.assertEqual(4, len(solution.actions))
        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(2,
                         migration_types.get("migrate", 0))
        self.assertEqual(2,
                         migration_types.get("retype", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_migrate_volumes_select_no_volumes(self):
        volume_on_src1 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src3@back1#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
        ]
        self.m_n_helper.get_instance_list.return_value = []
        solution = self.strategy.execute()
        self.assertEqual(0, len(solution.actions))

    def test_execute_live_migrate_instance_parallel(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1_1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1_2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1_1,
            instance_on_src1_2,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(2, migration_types.get("live", 0))
        global_efficacy_value = solution.global_efficacy[0].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_parallel_per_node(self):
        self.input_parameters["parallel_per_node"] = 1

        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1_1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1_2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1_1,
            instance_on_src1_2,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("live", 0))
        global_efficacy_value = solution.global_efficacy[0].get('value', 0)
        self.assertEqual(50.0, global_efficacy_value)

    def test_execute_migrate_volume_parallel(self):
        volume_on_src1_1 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_1"],
                                            name="volume_1")
        volume_on_src1_2 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_2"],
                                            name="volume_2")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1_1,
            volume_on_src1_2,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(2, migration_types.get("migrate", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(100, global_efficacy_value)

    def test_execute_parallel_per_pool(self):
        self.input_parameters["parallel_per_pool"] = 1

        volume_on_src1_1 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_1"],
                                            name="volume_1")
        volume_on_src1_2 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_2"],
                                            name="volume_2")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1_1,
            volume_on_src1_2,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("migrate", 0))
        global_efficacy_value = solution.global_efficacy[2].get('value', 0)
        self.assertEqual(50.0, global_efficacy_value)

    def test_execute_parallel_total(self):
        self.input_parameters["parallel_total"] = 1
        self.input_parameters["parallel_per_pool"] = 1

        volume_on_src1_1 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_1"],
                                            name="volume_1")
        volume_on_src1_2 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_2"],
                                            name="volume_2")
        volume_on_src2_1 = self.fake_volume(host="src2@back1#pool1",
                                            id=volume_uuid_mapping["volume_3"],
                                            name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1_1,
            volume_on_src1_2,
            volume_on_src2_1,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        solution = self.strategy.execute()

        migration_types = collections.Counter(
            [action.get('input_parameters')['migration_type']
             for action in solution.actions])
        self.assertEqual(1, migration_types.get("migrate", 0))

    def test_execute_mixed_instances_volumes(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1_1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src2_2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1_1,
            instance_on_src2_2,
        ]

        volume_on_src1_1 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_1"],
                                            name="volume_1")
        volume_on_src1_2 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_2"],
                                            name="volume_2")
        volume_on_src2_1 = self.fake_volume(host="src2@back1#pool1",
                                            id=volume_uuid_mapping["volume_3"],
                                            name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1_1,
            volume_on_src1_2,
            volume_on_src2_1,
        ]

        self.input_parameters["compute_nodes"] = [
            {"src_node": "src1", "dst_node": "dst1"},
        ]
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
        ]

        solution = self.strategy.execute()

        # Check volume migrations
        action_types = collections.Counter(
            [action['action_type']
             for action in solution.actions])
        expected_vmigrations = [
            {'action_type': 'volume_migrate',
             'input_parameters':
                {'migration_type': 'migrate',
                 'destination_node': 'dst1@back1#pool1',
                 'resource_name': 'volume_1',
                 'resource_id': '74454247-a064-4b34-8f43-89337987720e'}},
            {'action_type': 'volume_migrate',
             'input_parameters':
                {'migration_type': 'migrate',
                 'destination_node': 'dst1@back1#pool1',
                 'resource_name': 'volume_2',
                 'resource_id': 'a16c811e-2521-4fd3-8779-6a94ccb3be73'}}
        ]
        expected_vm_migrations = [
            {'action_type': 'migrate',
             'input_parameters':
                {'migration_type': 'live',
                 'source_node': 'src1',
                 'destination_node': 'dst1',
                 'resource_name': 'INSTANCE_1',
                 'resource_id': 'd010ef1f-dc19-4982-9383-087498bfde03'}}
        ]
        migrated_volumes = [action
                            for action in solution.actions
                            if action['action_type'] == 'volume_migrate']
        self.assertEqual(2, action_types.get("volume_migrate", 0))
        self.assertEqual(expected_vmigrations, migrated_volumes)

        self.assertEqual(1, action_types.get("migrate", 0))
        migrated_vms = [action
                        for action in solution.actions
                        if action['action_type'] == 'migrate']
        self.assertEqual(expected_vm_migrations, migrated_vms)

        # All the detached volumes in the pool should be migrated
        volume_indicator = [item['value'] for item in solution.global_efficacy
                            if item['name'] == "volume_migrate_ratio"][0]
        self.assertEqual(100, volume_indicator)
        # All the instances in src1 should be migrated
        live_ind = [item['value'] for item in solution.global_efficacy
                    if item['name'] == "live_instance_migrate_ratio"][0]
        self.assertEqual(100, live_ind)
        # check that the live migration is the third action, after all
        # volume migrations, since with_attached_volume=False in this test
        second_action = solution.actions[2]['input_parameters']
        self.assertEqual(second_action['migration_type'], 'live')

    def test_execute_mixed_instances_volumes_with_attached(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1_1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src2_2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1_3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1_1,
            instance_on_src2_2,
            instance_on_src1_3
        ]

        volume_on_src1_1 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_1"],
                                            name="volume_1")
        volume_on_src1_2 = self.fake_volume(host="src1@back1#pool1",
                                            id=volume_uuid_mapping["volume_2"],
                                            name="volume_2")
        volume_on_src2_1 = self.fake_volume(host="src2@back1#pool1",
                                            id=volume_uuid_mapping["volume_3"],
                                            name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1_1,
            volume_on_src1_2,
            volume_on_src2_1,
        ]

        volume_on_src1_1.status = 'in-use'
        volume_on_src1_1.attachments = [{
            "server_id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "attachment_id": "attachment1"
        }]

        self.input_parameters["compute_nodes"] = [
            {"src_node": "src1", "dst_node": "dst1"},
        ]
        self.input_parameters["storage_pools"] = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
        ]
        self.input_parameters["with_attached_volume"] = True

        self.m_n_helper.find_instance.return_value = instance_on_src1_3

        solution = self.strategy.execute()
        # Check migrations
        action_types = collections.Counter(
            [action['action_type']
             for action in solution.actions])
        expected_vol_migrations = [
            {'action_type': 'volume_migrate',
             'input_parameters':
                {'migration_type': 'migrate',
                 'destination_node': 'dst1@back1#pool1',
                 'resource_name': 'volume_1',
                 'resource_id': '74454247-a064-4b34-8f43-89337987720e'}},
            {'action_type': 'volume_migrate',
             'input_parameters':
                {'migration_type': 'migrate',
                 'destination_node': 'dst1@back1#pool1',
                 'resource_name': 'volume_2',
                 'resource_id': 'a16c811e-2521-4fd3-8779-6a94ccb3be73'}}
        ]
        expected_vm_migrations = [
            {'action_type': 'migrate',
             'input_parameters':
                {'migration_type': 'live',
                 'source_node': 'src1',
                 'destination_node': 'dst1',
                 'resource_name': 'INSTANCE_3',
                 'resource_id': 'd030ef1f-dc19-4982-9383-087498bfde03'}},
            {'action_type': 'migrate',
             'input_parameters':
                {'migration_type': 'live',
                 'source_node': 'src1',
                 'destination_node': 'dst1',
                 'resource_name': 'INSTANCE_1',
                 'resource_id': 'd010ef1f-dc19-4982-9383-087498bfde03'}}
        ]
        migrated_volumes = [action
                            for action in solution.actions
                            if action['action_type'] == 'volume_migrate']
        self.assertEqual(2, action_types.get("volume_migrate", 0))
        self.assertEqual(expected_vol_migrations, migrated_volumes)
        migrated_vms = [action
                        for action in solution.actions
                        if action['action_type'] == 'migrate']
        self.assertEqual(2, action_types.get("migrate", 0))
        self.assertEqual(expected_vm_migrations, migrated_vms)

        self.assertEqual(2, action_types.get("migrate", 0))
        # check that the live migration is the second action, before other
        # volume migrations
        second_action = solution.actions[1]['input_parameters']
        self.assertEqual(second_action['migration_type'], 'live')

        # All the detached volumes in the pool should be migrated
        volume_mig_ind = [item['value'] for item in solution.global_efficacy
                          if item['name'] == "volume_migrate_ratio"][0]
        self.assertEqual(100, volume_mig_ind)
        # All the attached volumes in the pool should be swapped
        volume_swap_ind = [item['value'] for item in solution.global_efficacy
                           if item['name'] == "volume_update_ratio"][0]
        self.assertEqual(100, volume_swap_ind)
        # All the instances in src1 should be migrated
        live_ind = [item['value'] for item in solution.global_efficacy
                    if item['name'] == "live_instance_migrate_ratio"][0]
        self.assertEqual(100, live_ind)

    def test_instance_migration_exists(self):

        fake_actions = [
            {'action_type': 'migrate', 'resource_id': 'instance1'},
            {'action_type': 'some_other_action', 'resource_id': 'instance2'},
            {'action_type': 'migrate', 'resource_id': 'instance3'}
        ]

        for action in fake_actions:
            self.strategy.solution.add_action(
                action['action_type'],
                resource_id=action['resource_id'])
        self.assertTrue(self.strategy._instance_migration_exists('instance1'))
        self.assertTrue(self.strategy._instance_migration_exists('instance3'))
        self.assertFalse(self.strategy._instance_migration_exists('instance2'))
        self.assertFalse(self.strategy._instance_migration_exists('instance4'))
        self.assertFalse(self.strategy._instance_migration_exists(None))
        self.assertFalse(self.strategy._instance_migration_exists(''))

    # priority filter #

    def test_get_priority_filter_list(self):
        self.input_parameters["priority"] = {
            "project": ["pj1"],
            "compute_node": ["compute1", "compute2"],
            "compute": ["cpu_num"],
            "storage_pool": ["pool1", "pool2"],
            "storage": ["size"]
        }
        filters = self.strategy.get_priority_filter_list()
        self.assertIn(strategies.zone_migration.ComputeHostSortFilter,
                      map(lambda l: l.__class__, filters))  # noqa: E741
        self.assertIn(strategies.zone_migration.StorageHostSortFilter,
                      map(lambda l: l.__class__, filters))  # noqa: E741
        self.assertIn(strategies.zone_migration.ProjectSortFilter,
                      map(lambda l: l.__class__, filters))  # noqa: E741

    # ComputeHostSortFilter #

    def test_filtered_targets_compute_nodes(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src3",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "vm_state": "active"
        }
        instance_on_src3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.input_parameters["priority"] = {
            "compute_node": ["src1", "src2"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src1, instance_on_src2])

    # StorageHostSortFilter #

    def test_filtered_targets_storage_pools(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1")
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2")
        volume_on_src3 = self.fake_volume(host="src3@back2#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        self.input_parameters["priority"] = {
            "storage_pool": ["src1@back1#pool1", "src2@back1#pool1"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get("volume"),
                         [volume_on_src1, volume_on_src2])

    # ProjectSortFilter #

    def test_filtered_targets_project(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "project_id": "pj2",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "project_id": "pj1",
            "vm_state": "active"
        }
        instance_on_src2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src3",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "project_id": "pj3",
            "vm_state": "active"
        }
        instance_on_src3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1",
                                          project_id="pj2")
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2",
                                          volume_type="type2",
                                          project_id="pj1")
        volume_on_src3 = self.fake_volume(host="src3@back2#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3",
                                          project_id="pj3")

        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
        ]

        self.input_parameters["priority"] = {
            "project": ["pj1"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])
        self.assertEqual(targets.get('volume'),
                         [volume_on_src2, volume_on_src1])
        self.assertEqual(targets,
                         {"instance": [instance_on_src2, instance_on_src1],
                          "volume": [volume_on_src2, volume_on_src1]})

    # ComputeSpecSortFilter #

    def test_filtered_targets_instance_mem_size(self):
        flavor_64 = self.create_openstacksdk_flavor(
            id="1", ram="64", vcpus=1, disk=1)
        flavor_128 = self.create_openstacksdk_flavor(
            id="2", ram=128, vcpus=1, disk=1)
        flavor_512 = self.create_openstacksdk_flavor(
            id="3", ram=512, vcpus=1, disk=1)
        self.m_n_helper.get_flavor_list.return_value = [
            flavor_64,
            flavor_128,
            flavor_512,
        ]

        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "1"},
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "2"},
            "vm_state": "active"
        }
        instance_on_src2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src3",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "3"},
            "vm_state": "active"
        }
        instance_on_src3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.input_parameters["priority"] = {
            "compute": ["mem_size"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])

    def test_filtered_targets_instance_vcpu_num(self):
        flavor_1 = self.create_openstacksdk_flavor(
            id="1", ram=1, vcpus=1, disk=1)
        flavor_2 = self.create_openstacksdk_flavor(
            id="2", ram=1, vcpus=2, disk=1)
        flavor_3 = self.create_openstacksdk_flavor(
            id="3", ram=1, vcpus=3, disk=1)
        self.m_n_helper.get_flavor_list.return_value = [
            flavor_1,
            flavor_2,
            flavor_3,
        ]

        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "1"},
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "2"},
            "vm_state": "active"
        }
        instance_on_src2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src3",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "3"},
            "vm_state": "active"
        }
        instance_on_src3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.input_parameters["priority"] = {
            "compute": ["vcpu_num"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])

    def test_filtered_targets_instance_disk_size(self):
        flavor_1 = self.create_openstacksdk_flavor(
            id="1", ram=1, vcpus=1, disk=1)
        flavor_2 = self.create_openstacksdk_flavor(
            id="2", ram=1, vcpus=1, disk=2)
        flavor_3 = self.create_openstacksdk_flavor(
            id="3", ram=1, vcpus=1, disk=3)
        self.m_n_helper.get_flavor_list.return_value = [
            flavor_1,
            flavor_2,
            flavor_3,
        ]

        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "1"},
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "2"},
            "vm_state": "active"
        }
        instance_on_src2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src3",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "flavor": {"id": "3"},
            "vm_state": "active"
        }
        instance_on_src3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.input_parameters["priority"] = {
            "compute": ["disk_size"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])

    def test_filtered_targets_instance_created_at(self):
        server_info = {
            "compute_host": "src1",
            "name": "INSTANCE_1",
            "id": "d010ef1f-dc19-4982-9383-087498bfde03",
            "created_at": "2017-10-30T00:00:00",
            "vm_state": "active"
        }
        instance_on_src1 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src2",
            "name": "INSTANCE_2",
            "id": "d020ef1f-dc19-4982-9383-087498bfde03",
            "created_at": "1977-03-29T03:03:03",
            "vm_state": "active"
        }
        instance_on_src2 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        server_info = {
            "compute_host": "src3",
            "name": "INSTANCE_3",
            "id": "d030ef1f-dc19-4982-9383-087498bfde03",
            "created_at": "1977-03-29T03:03:03",
            "vm_state": "active"
        }
        instance_on_src3 = nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**server_info)
        )
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.input_parameters["priority"] = {
            "compute": ["created_at"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])

    # StorageSpecSortFilter #

    def test_filtered_targets_storage_size(self):
        volume_on_src1 = self.fake_volume(
            host="src1@back1#pool1",
            size="1",
            id=volume_uuid_mapping["volume_1"],
            name="volume_1")
        volume_on_src2 = self.fake_volume(
            host="src2@back1#pool1",
            size="2",
            id=volume_uuid_mapping["volume_2"],
            volume_type="type2",
            name="volume_2")
        volume_on_src3 = self.fake_volume(
            host="src3@back2#pool1",
            size="3",
            id=volume_uuid_mapping["volume_3"],
            name="volume_3")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        self.input_parameters["priority"] = {
            "storage": ["size"]
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get("volume"),
                         [volume_on_src2, volume_on_src1])

    def test_filtered_targets_storage_created_at(self):
        volume_on_src1 = self.fake_volume(host="src1@back1#pool1",
                                          id=volume_uuid_mapping["volume_1"],
                                          name="volume_1",
                                          created_at="2017-10-30T00:00:00")
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          volume_type="type2",
                                          name="volume_2",
                                          created_at="1977-03-29T03:03:03")
        volume_on_src3 = self.fake_volume(host="src3@back2#pool1",
                                          id=volume_uuid_mapping["volume_3"],
                                          name="volume_3",
                                          created_at="1977-03-29T03:03:03")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src1,
            volume_on_src2,
            volume_on_src3,
        ]

        self.m_n_helper.get_instance_list.return_value = []

        self.input_parameters["priority"] = {
            "storage": ["created_at"]
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get("volume"),
                         [volume_on_src2, volume_on_src1])
