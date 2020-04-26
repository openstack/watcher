# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
#
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

import os_resource_classes as orc
from unittest import mock

from watcher.common import nova_helper
from watcher.common import placement_helper
from watcher.decision_engine.model.collector import nova
from watcher.tests import base
from watcher.tests import conf_fixture


class TestNovaClusterDataModelCollector(base.TestCase):

    def setUp(self):
        super(TestNovaClusterDataModelCollector, self).setUp()
        self.useFixture(conf_fixture.ConfReloadFixture())

    @mock.patch('keystoneclient.v3.client.Client', mock.Mock())
    @mock.patch.object(placement_helper, 'PlacementHelper')
    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_nova_cdmc_execute(self, m_nova_helper_cls,
                               m_placement_helper_cls):
        m_placement_helper = mock.Mock(name="placement_helper")
        m_placement_helper.get_inventories.return_value = {
            orc.VCPU: {
                "allocation_ratio": 16.0,
                "total": 8,
                "reserved": 0,
                "step_size": 1,
                "min_unit": 1,
                "max_unit": 8},
            orc.MEMORY_MB: {
                "allocation_ratio": 1.5,
                "total": 16039,
                "reserved": 512,
                "step_size": 1,
                "min_unit": 1,
                "max_unit": 16039},
            orc.DISK_GB: {
                "allocation_ratio": 1.0,
                "total": 142,
                "reserved": 0,
                "step_size": 1,
                "min_unit": 1,
                "max_unit": 142}
        }
        m_placement_helper.get_usages_for_resource_provider.return_value = {
            orc.DISK_GB: 10,
            orc.MEMORY_MB: 100,
            orc.VCPU: 0
        }
        m_placement_helper_cls.return_value = m_placement_helper
        m_nova_helper = mock.Mock(name="nova_helper")
        m_nova_helper_cls.return_value = m_nova_helper
        m_nova_helper.get_service.return_value = mock.Mock(
            id=1355,
            host='test_hostname',
            binary='nova-compute',
            status='enabled',
            state='up',
            disabled_reason='',
        )
        minimal_node = dict(
            id='160a0e7b-8b0b-4854-8257-9c71dff4efcc',
            hypervisor_hostname='test_hostname',
            state='TEST_STATE',
            status='TEST_STATUS',
        )
        minimal_node_with_servers = dict(
            servers=[
                {'name': 'fake_instance',
                 'uuid': 'ef500f7e-dac8-470f-960c-169486fce71b'}
            ],
            **minimal_node
        )
        fake_compute_node = mock.Mock(
            service={'id': 123, 'host': 'test_hostname',
                     'disabled_reason': ''},
            memory_mb=333,
            memory_mb_used=100,
            free_disk_gb=222,
            local_gb=111,
            local_gb_used=10,
            vcpus=4,
            vcpus_used=0,
            servers=None,  # Don't let the mock return a value for servers.
            **minimal_node
        )
        fake_detailed_node = mock.Mock(
            service={'id': 123, 'host': 'test_hostname',
                     'disabled_reason': ''},
            memory_mb=333,
            memory_mb_used=100,
            free_disk_gb=222,
            local_gb=111,
            local_gb_used=10,
            vcpus=4,
            vcpus_used=0,
            **minimal_node_with_servers)
        fake_instance = mock.Mock(
            id='ef500f7e-dac8-470f-960c-169486fce71b',
            name='fake_instance',
            flavor={'ram': 333, 'disk': 222, 'vcpus': 4, 'id': 1},
            metadata={'hi': 'hello'},
            tenant_id='ff560f7e-dbc8-771f-960c-164482fce21b',
        )
        setattr(fake_instance, 'OS-EXT-STS:vm_state', 'VM_STATE')
        setattr(fake_instance, 'name', 'fake_instance')
        # Returns the hypervisors with details (service) but no servers.
        m_nova_helper.get_compute_node_list.return_value = [fake_compute_node]
        # Returns the hypervisor with servers and details (service).
        m_nova_helper.get_compute_node_by_name.return_value = [
            fake_detailed_node]
        # Returns the hypervisor with details (service) but no servers.
        m_nova_helper.get_instance_list.return_value = [fake_instance]

        m_config = mock.Mock()
        m_osc = mock.Mock()

        nova_cdmc = nova.NovaClusterDataModelCollector(
            config=m_config, osc=m_osc)

        nova_cdmc.get_audit_scope_handler([])
        model = nova_cdmc.execute()

        compute_nodes = model.get_all_compute_nodes()
        instances = model.get_all_instances()

        self.assertEqual(1, len(compute_nodes))
        self.assertEqual(1, len(instances))

        node = list(compute_nodes.values())[0]
        instance = list(instances.values())[0]

        self.assertEqual(node.uuid, '160a0e7b-8b0b-4854-8257-9c71dff4efcc')
        self.assertEqual(instance.uuid, 'ef500f7e-dac8-470f-960c-169486fce71b')

        memory_total = (node.memory-node.memory_mb_reserved)*node.memory_ratio
        self.assertEqual(node.memory_mb_capacity, memory_total)

        disk_total = (node.disk-node.disk_gb_reserved)*node.disk_ratio
        self.assertEqual(node.disk_gb_capacity, disk_total)

        vcpus_total = (node.vcpus-node.vcpu_reserved)*node.vcpu_ratio
        self.assertEqual(node.vcpu_capacity, vcpus_total)

        m_nova_helper.get_compute_node_by_name.assert_called_once_with(
            minimal_node['hypervisor_hostname'], servers=True, detailed=True)
        m_nova_helper.get_instance_list.assert_called_once_with(
            filters={'host': fake_compute_node.service['host']}, limit=1)


class TestNovaModelBuilder(base.TestCase):

    @mock.patch.object(nova_helper, 'NovaHelper', mock.MagicMock())
    def test_add_instance_node(self):
        model_builder = nova.NovaModelBuilder(osc=mock.MagicMock())
        model_builder.model = mock.MagicMock()
        mock_node = mock.MagicMock()
        mock_host = mock_node.service["host"]
        inst1 = mock.MagicMock(
            id='ef500f7e-dac8-470f-960c-169486fce711',
            tenant_id='ff560f7e-dbc8-771f-960c-164482fce21b')
        setattr(inst1, 'OS-EXT-STS:vm_state', 'deleted')
        setattr(inst1, 'name', 'instance1')
        inst2 = mock.MagicMock(
            id='ef500f7e-dac8-470f-960c-169486fce722',
            tenant_id='ff560f7e-dbc8-771f-960c-164482fce21b')
        setattr(inst2, 'OS-EXT-STS:vm_state', 'active')
        setattr(inst2, 'name', 'instance2')
        mock_instances = [inst1, inst2]
        model_builder.nova_helper.get_instance_list.return_value = (
            mock_instances)
        model_builder.add_instance_node(mock_node, mock_instances)
        # verify that when len(instances) <= 1000, limit == len(instance).
        model_builder.nova_helper.get_instance_list.assert_called_once_with(
            filters={'host': mock_host}, limit=2)
        fake_instance = model_builder._build_instance_node(inst2)
        model_builder.model.add_instance.assert_called_once_with(
            fake_instance)

        # verify that when len(instances) > 1000, limit == -1.
        mock_instance = mock.Mock()
        mock_instances = [mock_instance] * 1001
        model_builder.add_instance_node(mock_node, mock_instances)
        model_builder.nova_helper.get_instance_list.assert_called_with(
            filters={'host': mock_host}, limit=-1)

    def test_check_model(self):
        """Initialize collector ModelBuilder and test check model"""

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope))

    def test_check_model_update_false(self):
        """Initialize check model with multiple identical scopes

        The seconds check_model should return false as the models are the same
        """

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope))
        self.assertFalse(t_nova_cluster._check_model_scope(m_scope))

    def test_check_model_update_true(self):
        """Initialize check model with multiple different scopes

        Since the models differ both should return True for the update flag
        """

        m_scope_one = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        m_scope_two = [{"compute": [
            {"host_aggregates": [{"id": 2}]},
            {"availability_zones": [{"name": "av_b"}]}
        ]}]

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope_one))
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope_two))

    def test_merge_compute_scope(self):
        """"""

        m_scope_one = [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]

        m_scope_two = [
            {"host_aggregates": [{"id": 4}]},
            {"availability_zones": [{"name": "av_b"}]}
        ]

        reference = {'availability_zones':
                     [{'name': 'av_a'}, {'name': 'av_b'}],
                     'host_aggregates':
                     [{'id': 5}, {'id': 4}]}

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        t_nova_cluster._merge_compute_scope(m_scope_one)
        t_nova_cluster._merge_compute_scope(m_scope_two)

        self.assertEqual(reference, t_nova_cluster.model_scope)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_collect_aggregates(self, m_nova):
        """"""

        m_nova.return_value.get_aggregate_list.return_value = \
            [mock.Mock(id=1, name='example'),
             mock.Mock(id=5, name='example', hosts=['hostone', 'hosttwo'])]

        m_nova.return_value.get_compute_node_by_name.return_value = False

        m_scope = [{'id': 5}]

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        result = set()
        t_nova_cluster._collect_aggregates(m_scope, result)

        self.assertEqual(set(['hostone', 'hosttwo']), result)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_collect_aggregates_none(self, m_nova):
        """Test collect_aggregates with host_aggregates None"""
        result = set()
        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        t_nova_cluster._collect_aggregates(None, result)

        self.assertEqual(set(), result)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_collect_zones(self, m_nova):
        """"""

        m_nova.return_value.get_service_list.return_value = \
            [mock.Mock(zone='av_b'),
             mock.Mock(zone='av_a', host='hostone')]

        m_nova.return_value.get_compute_node_by_name.return_value = False

        m_scope = [{'name': 'av_a'}]

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        result = set()
        t_nova_cluster._collect_zones(m_scope, result)

        self.assertEqual(set(['hostone']), result)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_collect_zones_none(self, m_nova):
        """Test collect_zones with availability_zones None"""
        result = set()
        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        t_nova_cluster._collect_zones(None, result)

        self.assertEqual(set(), result)

    @mock.patch.object(placement_helper, 'PlacementHelper')
    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_add_physical_layer(self, m_nova, m_placement):
        """Ensure all three steps of the physical layer are fully executed

        First the return value for get_aggregate_list and get_service_list are
        mocked. These return 3 hosts of which hostone is returned by both the
        aggregate and service call. This will help verify the elimination of
        duplicates. The scope is setup so that only hostone and hosttwo should
        remain.

        There will be 2 simulated compute nodes and 2 associated instances.
        These will be returned by their matching calls in nova helper. The
        calls to get_compute_node_by_name and get_instance_list are asserted
        as to verify the correct operation of add_physical_layer.
        """

        mock_placement = mock.Mock(name="placement_helper")
        mock_placement.get_inventories.return_value = dict()
        mock_placement.get_usages_for_resource_provider.return_value = None
        m_placement.return_value = mock_placement

        m_nova.return_value.get_aggregate_list.return_value = \
            [mock.Mock(id=1, name='example'),
             mock.Mock(id=5, name='example', hosts=['hostone', 'hosttwo'])]

        m_nova.return_value.get_service_list.return_value = \
            [mock.Mock(zone='av_b', host='hostthree'),
             mock.Mock(zone='av_a', host='hostone')]

        compute_node_one = mock.Mock(
            id='796fee99-65dd-4262-aa-fd2a1143faa6',
            hypervisor_hostname='hostone',
            hypervisor_type='QEMU',
            state='TEST_STATE',
            status='TEST_STATUS',
            memory_mb=333,
            memory_mb_used=100,
            free_disk_gb=222,
            local_gb=111,
            local_gb_used=10,
            vcpus=4,
            vcpus_used=0,
            servers=[
                {'name': 'fake_instance',
                 'uuid': 'ef500f7e-dac8-470f-960c-169486fce71b'}
            ],
            service={'id': 123, 'host': 'hostone',
                     'disabled_reason': ''},
        )

        compute_node_two = mock.Mock(
            id='756fef99-65dd-4262-aa-fd2a1143faa6',
            hypervisor_hostname='hosttwo',
            hypervisor_type='QEMU',
            state='TEST_STATE',
            status='TEST_STATUS',
            memory_mb=333,
            memory_mb_used=100,
            free_disk_gb=222,
            local_gb=111,
            local_gb_used=10,
            vcpus=4,
            vcpus_used=0,
            servers=[
                {'name': 'fake_instance2',
                 'uuid': 'ef500f7e-dac8-47f0-960c-169486fce71b'}
            ],
            service={'id': 123, 'host': 'hosttwo',
                     'disabled_reason': ''},
        )

        m_nova.return_value.get_compute_node_by_name.side_effect = [
            [compute_node_one], [compute_node_two]
        ]

        fake_instance_one = mock.Mock(
            id='796fee99-65dd-4262-aa-fd2a1143faa6',
            name='fake_instance',
            flavor={'ram': 333, 'disk': 222, 'vcpus': 4, 'id': 1},
            metadata={'hi': 'hello'},
            tenant_id='ff560f7e-dbc8-771f-960c-164482fce21b',
        )
        fake_instance_two = mock.Mock(
            id='ef500f7e-dac8-47f0-960c-169486fce71b',
            name='fake_instance2',
            flavor={'ram': 333, 'disk': 222, 'vcpus': 4, 'id': 1},
            metadata={'hi': 'hello'},
            tenant_id='756fef99-65dd-4262-aa-fd2a1143faa6',
        )
        m_nova.return_value.get_instance_list.side_effect = [
            [fake_instance_one], [fake_instance_two]
        ]

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        t_nova_cluster.execute(m_scope)
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hostone', servers=True, detailed=True)
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hosttwo', servers=True, detailed=True)
        self.assertEqual(
            m_nova.return_value.get_compute_node_by_name.call_count, 2)

        m_nova.return_value.get_instance_list.assert_any_call(
            filters={'host': 'hostone'}, limit=1)
        m_nova.return_value.get_instance_list.assert_any_call(
            filters={'host': 'hosttwo'}, limit=1)
        self.assertEqual(
            m_nova.return_value.get_instance_list.call_count, 2)

    @mock.patch.object(placement_helper, 'PlacementHelper')
    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_add_physical_layer_with_baremetal_node(self, m_nova,
                                                    m_placement_helper):
        """"""
        mock_placement = mock.Mock(name="placement_helper")
        mock_placement.get_inventories.return_value = dict()
        mock_placement.get_usages_for_resource_provider.return_value = None
        m_placement_helper.return_value = mock_placement
        m_nova.return_value.get_aggregate_list.return_value = \
            [mock.Mock(id=1, name='example'),
             mock.Mock(id=5, name='example', hosts=['hostone', 'hosttwo'])]

        m_nova.return_value.get_service_list.return_value = \
            [mock.Mock(zone='av_b', host='hostthree'),
             mock.Mock(zone='av_a', host='hostone')]

        compute_node = mock.Mock(
            id='796fee99-65dd-4262-aa-fd2a1143faa6',
            hypervisor_hostname='hostone',
            hypervisor_type='QEMU',
            state='TEST_STATE',
            status='TEST_STATUS',
            memory_mb=333,
            memory_mb_used=100,
            free_disk_gb=222,
            local_gb=111,
            local_gb_used=10,
            vcpus=4,
            vcpus_used=0,
            servers=[
                {'name': 'fake_instance',
                 'uuid': 'ef500f7e-dac8-470f-960c-169486fce71b'}
            ],
            service={'id': 123, 'host': 'hostone',
                     'disabled_reason': ''},
        )

        baremetal_node = mock.Mock(
            id='5f2d1b3d-4099-4623-b9-05148aefd6cb',
            hypervisor_hostname='hosttwo',
            hypervisor_type='ironic',
            state='TEST_STATE',
            status='TEST_STATUS',
        )

        m_nova.return_value.get_compute_node_by_name.side_effect = [
            [compute_node], [baremetal_node]]

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.NovaModelBuilder(mock.Mock())
        model = t_nova_cluster.execute(m_scope)

        compute_nodes = model.get_all_compute_nodes()
        self.assertEqual(1, len(compute_nodes))
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hostone', servers=True, detailed=True)
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hosttwo', servers=True, detailed=True)
        self.assertEqual(
            m_nova.return_value.get_compute_node_by_name.call_count, 2)
