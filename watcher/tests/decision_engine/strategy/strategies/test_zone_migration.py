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
from unittest import mock

import cinderclient
import novaclient
from watcher.common import cinder_helper
from watcher.common import clients
from watcher.common import nova_helper
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy

volume_uuid_mapping = faker_cluster_state.volume_uuid_mapping


class TestZoneMigration(TestBaseStrategy):

    def setUp(self):
        super(TestZoneMigration, self).setUp()

        # fake storage cluster
        self.fake_s_cluster = faker_cluster_state.FakerStorageModelCollector()

        p_s_model = mock.patch.object(
            strategies.ZoneMigration, "storage_model",
            new_callable=mock.PropertyMock)
        self.m_s_model = p_s_model.start()
        self.addCleanup(p_s_model.stop)

        p_migrate_compute_nodes = mock.patch.object(
            strategies.ZoneMigration, "migrate_compute_nodes",
            new_callable=mock.PropertyMock)
        self.m_migrate_compute_nodes = p_migrate_compute_nodes.start()
        self.addCleanup(p_migrate_compute_nodes.stop)

        p_migrate_storage_pools = mock.patch.object(
            strategies.ZoneMigration, "migrate_storage_pools",
            new_callable=mock.PropertyMock)
        self.m_migrate_storage_pools = p_migrate_storage_pools.start()
        self.addCleanup(p_migrate_storage_pools.stop)

        p_parallel_total = mock.patch.object(
            strategies.ZoneMigration, "parallel_total",
            new_callable=mock.PropertyMock)
        self.m_parallel_total = p_parallel_total.start()
        self.addCleanup(p_parallel_total.stop)

        p_parallel_per_node = mock.patch.object(
            strategies.ZoneMigration, "parallel_per_node",
            new_callable=mock.PropertyMock)
        self.m_parallel_per_node = p_parallel_per_node.start()
        self.addCleanup(p_parallel_per_node.stop)

        p_parallel_per_pool = mock.patch.object(
            strategies.ZoneMigration, "parallel_per_pool",
            new_callable=mock.PropertyMock)
        self.m_parallel_per_pool = p_parallel_per_pool.start()
        self.addCleanup(p_parallel_per_pool.stop)

        p_priority = mock.patch.object(
            strategies.ZoneMigration, "priority",
            new_callable=mock.PropertyMock
        )
        self.m_priority = p_priority.start()
        self.addCleanup(p_priority.stop)

        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model

        model = self.fake_s_cluster.generate_scenario_1()
        self.m_s_model.return_value = model

        self.m_parallel_total.return_value = 6
        self.m_parallel_per_node.return_value = 2
        self.m_parallel_per_pool.return_value = 2
        self.m_audit_scope.return_value = mock.Mock()
        self.m_migrate_compute_nodes.return_value = [
            {"src_node": "src1", "dst_node": "dst1"},
            {"src_node": "src2", "dst_node": "dst2"}
        ]
        self.m_migrate_storage_pools.return_value = [
            {"src_pool": "src1@back1#pool1", "dst_pool": "dst1@back1#pool1",
             "src_type": "type1", "dst_type": "type1"},
            {"src_pool": "src2@back1#pool1", "dst_pool": "dst2@back2#pool1",
             "src_type": "type2", "dst_type": "type3"}
        ]

        self.strategy = strategies.ZoneMigration(
            config=mock.Mock())

        self.m_osc_cls = mock.Mock()
        self.m_osc = mock.Mock(spec=clients.OpenStackClients)
        self.m_osc_cls.return_value = self.m_osc
        m_openstack_clients = mock.patch.object(
            clients, "OpenStackClients", self.m_osc_cls)
        m_openstack_clients.start()
        self.addCleanup(m_openstack_clients.stop)

        self.m_n_helper_cls = mock.Mock()
        self.m_n_helper = mock.Mock(spec=nova_helper.NovaHelper)
        self.m_n_helper_cls.return_value = self.m_n_helper
        m_nova_helper = mock.patch.object(
            nova_helper, "NovaHelper", self.m_n_helper_cls)
        m_nova_helper.start()
        self.addCleanup(m_nova_helper.stop)

        self.m_c_helper_cls = mock.Mock()
        self.m_c_helper = mock.Mock(spec=cinder_helper.CinderHelper)
        self.m_c_helper_cls.return_value = self.m_c_helper
        m_cinder_helper = mock.patch.object(
            cinder_helper, "CinderHelper", self.m_c_helper_cls)
        m_cinder_helper.start()
        self.addCleanup(m_cinder_helper.stop)

    @staticmethod
    def fake_instance(**kwargs):
        instance = mock.MagicMock(spec=novaclient.v2.servers.Server)
        instance.id = kwargs.get('id', utils.generate_uuid())
        instance.name = kwargs.get('name', 'fake_name')
        instance.status = kwargs.get('status', 'ACTIVE')
        instance.tenant_id = kwargs.get('project_id', None)
        instance.flavor = {'id': kwargs.get('flavor_id', None)}
        setattr(instance, 'OS-EXT-SRV-ATTR:host', kwargs.get('host'))
        setattr(instance, 'created_at',
                kwargs.get('created_at', '1977-01-01T00:00:00'))
        setattr(instance, 'OS-EXT-STS:vm_state', kwargs.get('state', 'active'))

        return instance

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
        instance_on_src1 = self.fake_instance(
            host="src1",
            id="INSTANCE_1",
            name="INSTANCE_1")
        instance_on_src2 = self.fake_instance(
            host="src2",
            id="INSTANCE_2",
            name="INSTANCE_2")
        instance_on_src3 = self.fake_instance(
            host="src3",
            id="INSTANCE_3",
            name="INSTANCE_3")
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

        # src1,src2 is in instances
        # src3 is not in instances
        self.assertIn(volume_on_src1, volumes)
        self.assertIn(volume_on_src2, volumes)
        self.assertNotIn(volume_on_src3, volumes)

    # execute #

    def test_execute_live_migrate_instance(self):
        instance_on_src1 = self.fake_instance(
            host="src1",
            id="INSTANCE_1",
            name="INSTANCE_1")
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

    def test_execute_cold_migrate_instance(self):
        instance_on_src1 = self.fake_instance(
            host="src1",
            id="INSTANCE_1",
            name="INSTANCE_1")
        setattr(instance_on_src1, "status", "SHUTOFF")
        setattr(instance_on_src1, "OS-EXT-STS:vm_state", "stopped")
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

    def test_execute_retype_volume(self):
        volume_on_src2 = self.fake_volume(host="src2@back1#pool1",
                                          id=volume_uuid_mapping["volume_2"],
                                          name="volume_2")
        self.m_c_helper.get_volume_list.return_value = [
            volume_on_src2,
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

    def test_execute_live_migrate_instance_parallel(self):
        instance_on_src1_1 = self.fake_instance(
            host="src1",
            id="INSTANCE_1",
            name="INSTANCE_1")
        instance_on_src1_2 = self.fake_instance(
            host="src2",
            id="INSTANCE_2",
            name="INSTANCE_2")
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
        self.m_parallel_per_node.return_value = 1

        instance_on_src1_1 = self.fake_instance(
            host="src1",
            id="INSTANCE_1",
            name="INSTANCE_1")
        instance_on_src1_2 = self.fake_instance(
            host="src1",
            id="INSTANCE_2",
            name="INSTANCE_2")
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
        self.m_parallel_per_pool.return_value = 1

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
        self.m_parallel_total.return_value = 1
        self.m_parallel_per_pool.return_value = 1

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

    # priority filter #

    def test_get_priority_filter_list(self):
        self.m_priority.return_value = {
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
        instance_on_src1 = self.fake_instance(
            host="src1",
            id="INSTANCE_1",
            name="INSTANCE_1")
        instance_on_src2 = self.fake_instance(
            host="src2",
            id="INSTANCE_2",
            name="INSTANCE_2")
        instance_on_src3 = self.fake_instance(
            host="src3",
            id="INSTANCE_3",
            name="INSTANCE_3")
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.m_priority.return_value = {
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

        self.m_priority.return_value = {
            "storage_pool": ["src1@back1#pool1", "src2@back1#pool1"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get("volume"),
                         [volume_on_src1, volume_on_src2])

    # ProjectSortFilter #

    def test_filtered_targets_project(self):
        instance_on_src1 = self.fake_instance(
            host="src1", id="INSTANCE_1", name='INSTANCE_1', project_id="pj2")
        instance_on_src2 = self.fake_instance(
            host="src2", id="INSTANCE_2", name='INSTANCE_2', project_id="pj1")
        instance_on_src3 = self.fake_instance(
            host="src3", id="INSTANCE_3", name='INSTANCE_3', project_id="pj3")
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

        self.m_priority.return_value = {
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
        flavor_64 = self.fake_flavor(id="1", mem_size="64")
        flavor_128 = self.fake_flavor(id="2", mem_size="128")
        flavor_512 = self.fake_flavor(id="3", mem_size="512")
        self.m_n_helper.get_flavor_list.return_value = [
            flavor_64,
            flavor_128,
            flavor_512,
        ]

        instance_on_src1 = self.fake_instance(host="src1", name="INSTANCE_1",
                                              id="INSTANCE_1", flavor_id="1")
        instance_on_src2 = self.fake_instance(host="src2", name="INSTANCE_2",
                                              id="INSTANCE_2", flavor_id="2")
        instance_on_src3 = self.fake_instance(host="src3", name="INSTANCE_3",
                                              id="INSTANCE_3", flavor_id="3")
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.m_priority.return_value = {
            "compute": ["mem_size"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])

    def test_filtered_targets_instance_vcpu_num(self):
        flavor_1 = self.fake_flavor(id="1", vcpu_num="1")
        flavor_2 = self.fake_flavor(id="2", vcpu_num="2")
        flavor_3 = self.fake_flavor(id="3", vcpu_num="3")
        self.m_n_helper.get_flavor_list.return_value = [
            flavor_1,
            flavor_2,
            flavor_3,
        ]

        instance_on_src1 = self.fake_instance(host="src1", name="INSTANCE_1",
                                              id="INSTANCE_1", flavor_id="1")
        instance_on_src2 = self.fake_instance(host="src2", name="INSTANCE_2",
                                              id="INSTANCE_2", flavor_id="2")
        instance_on_src3 = self.fake_instance(host="src3", name="INSTANCE_3",
                                              id="INSTANCE_3", flavor_id="3")
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.m_priority.return_value = {
            "compute": ["vcpu_num"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])

    def test_filtered_targets_instance_disk_size(self):
        flavor_1 = self.fake_flavor(id="1", disk_size="1")
        flavor_2 = self.fake_flavor(id="2", disk_size="2")
        flavor_3 = self.fake_flavor(id="3", disk_size="3")
        self.m_n_helper.get_flavor_list.return_value = [
            flavor_1,
            flavor_2,
            flavor_3,
        ]

        instance_on_src1 = self.fake_instance(host="src1", name="INSTANCE_1",
                                              id="INSTANCE_1", flavor_id="1")
        instance_on_src2 = self.fake_instance(host="src2", name="INSTANCE_2",
                                              id="INSTANCE_2", flavor_id="2")
        instance_on_src3 = self.fake_instance(host="src3", name="INSTANCE_3",
                                              id="INSTANCE_3", flavor_id="3")
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.m_priority.return_value = {
            "compute": ["disk_size"],
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get('instance'),
                         [instance_on_src2, instance_on_src1])

    def test_filtered_targets_instance_created_at(self):
        instance_on_src1 = self.fake_instance(
            host="src1", id="INSTANCE_1",
            name="INSTANCE_1", created_at="2017-10-30T00:00:00")
        instance_on_src2 = self.fake_instance(
            host="src2", id="INSTANCE_2",
            name="INSTANCE_2", created_at="1977-03-29T03:03:03")
        instance_on_src3 = self.fake_instance(
            host="src3", id="INSTANCE_3",
            name="INSTANCE_3", created_at="1977-03-29T03:03:03")
        self.m_n_helper.get_instance_list.return_value = [
            instance_on_src1,
            instance_on_src2,
            instance_on_src3,
        ]

        self.m_c_helper.get_volume_list.return_value = []

        self.m_priority.return_value = {
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

        self.m_priority.return_value = {
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

        self.m_priority.return_value = {
            "storage": ["created_at"]
        }

        targets = self.strategy.filtered_targets()
        self.assertEqual(targets.get("volume"),
                         [volume_on_src2, volume_on_src1])
