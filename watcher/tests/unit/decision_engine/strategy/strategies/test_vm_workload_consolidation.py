#
# Authors: Vojtech CIMA <cima@zhaw.ch>
#          Bruno GRAZIOLI <gaea@zhaw.ch>
#          Sean MURPHY <murp@zhaw.ch>
#
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
#

from unittest import mock

from watcher.decision_engine.model import element
from watcher.decision_engine.solution.base import BaseSolution
from watcher.decision_engine.strategy import strategies
from watcher.tests.unit.decision_engine.model import faker_cluster_and_metrics
from watcher.tests.unit.decision_engine.strategy.strategies.test_base import (
    TestBaseStrategy,
)


class TestVMWorkloadConsolidation(TestBaseStrategy):
    scenarios = [
        (
            "Gnocchi",
            {
                "datasource": "gnocchi",
                "fake_datasource_cls": (
                    faker_cluster_and_metrics.FakeGnocchiMetrics
                ),
            },
        )
    ]

    def setUp(self):
        super().setUp()

        # fake cluster
        self.fake_c_cluster = faker_cluster_and_metrics.FakerModelCollector()

        p_datasource = mock.patch.object(
            strategies.VMWorkloadConsolidation,
            'datasource_backend',
            new_callable=mock.PropertyMock,
        )
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        # fake metrics
        self.fake_metrics = self.fake_datasource_cls(
            self.m_c_model.return_value
        )

        self.m_datasource.return_value = mock.Mock(
            get_instance_cpu_usage=(self.fake_metrics.get_instance_cpu_util),
            get_instance_ram_usage=(self.fake_metrics.get_instance_ram_util),
            get_instance_root_disk_size=(
                self.fake_metrics.get_instance_disk_root_size
            ),
            get_host_cpu_usage=(self.fake_metrics.get_compute_node_cpu_util),
            get_host_ram_usage=(self.fake_metrics.get_compute_node_ram_util),
        )
        self.strategy = strategies.VMWorkloadConsolidation(
            config=mock.Mock(datasources=self.datasource)
        )

    def test_get_instance_utilization(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_util = dict(cpu=1.0, ram=1, disk=10)
        self.assertEqual(
            instance_util, self.strategy.get_instance_utilization(instance_0)
        )

    def test_get_node_utilization(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_util = dict(cpu=1.0, ram=1, disk=10)
        self.assertEqual(node_util, self.strategy.get_node_utilization(node_0))

    def test_get_node_utilization_using_host_metrics(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")

        # "get_node_utilization" is expected to return the maximum
        # between the host metrics and the sum of the instance metrics.
        data_src = self.m_datasource.return_value
        cpu_usage = 30
        data_src.get_host_cpu_usage = mock.Mock(return_value=cpu_usage)
        data_src.get_host_ram_usage = mock.Mock(return_value=512 * 1024)

        exp_cpu_usage = cpu_usage * node_0.vcpus / 100
        exp_node_util = dict(cpu=exp_cpu_usage, ram=512, disk=10)
        self.assertEqual(
            exp_node_util, self.strategy.get_node_utilization(node_0)
        )

    def test_get_node_utilization_after_migrations(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_1 = model.get_node_by_uuid("Node_1")

        data_src = self.m_datasource.return_value
        cpu_usage = 30
        host_ram_usage_mb = 512
        data_src.get_host_cpu_usage = mock.Mock(return_value=cpu_usage)
        data_src.get_host_ram_usage = mock.Mock(
            return_value=host_ram_usage_mb * 1024
        )

        instance_uuid = 'INSTANCE_0'
        instance = model.get_instance_by_uuid(instance_uuid)
        self.strategy.add_migration(instance, node_0, node_1)

        instance_util = self.strategy.get_instance_utilization(instance)

        # Ensure that we take into account planned migrations when
        # determining node utilization
        exp_node_0_cpu_usage = (
            cpu_usage * node_0.vcpus
        ) / 100 - instance_util['cpu']
        exp_node_1_cpu_usage = (
            cpu_usage * node_1.vcpus
        ) / 100 + instance_util['cpu']

        exp_node_0_ram_usage = host_ram_usage_mb - instance.memory
        exp_node_1_ram_usage = host_ram_usage_mb + instance.memory

        exp_node_0_util = dict(
            cpu=exp_node_0_cpu_usage, ram=exp_node_0_ram_usage, disk=0
        )
        exp_node_1_util = dict(
            cpu=exp_node_1_cpu_usage, ram=exp_node_1_ram_usage, disk=25
        )

        self.assertEqual(
            exp_node_0_util, self.strategy.get_node_utilization(node_0)
        )
        self.assertEqual(
            exp_node_1_util, self.strategy.get_node_utilization(node_1)
        )

    def test_get_node_capacity(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_util = dict(cpu=40, ram=64, disk=250)
        self.assertEqual(node_util, self.strategy.get_node_capacity(node_0))

    def test_get_relative_node_utilization(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node = model.get_node_by_uuid('Node_0')
        rhu = self.strategy.get_relative_node_utilization(node)
        expected_rhu = {'disk': 0.04, 'ram': 0.015625, 'cpu': 0.025}
        self.assertEqual(expected_rhu, rhu)

    def test_get_relative_cluster_utilization(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        cru = self.strategy.get_relative_cluster_utilization()
        expected_cru = {'cpu': 0.05, 'disk': 0.05, 'ram': 0.0234375}
        self.assertEqual(expected_cru, cru)

    def _test_add_migration(
        self,
        instance_state,
        expect_migration=True,
        expected_migration_type="live",
    ):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        instance_uuid = 'INSTANCE_0'
        instance = model.get_instance_by_uuid(instance_uuid)
        instance.state = instance_state
        self.strategy.add_migration(instance, n1, n2)

        if expect_migration:
            self.assertEqual(1, len(self.strategy.solution.actions))

            expected = {
                'action_type': 'migrate',
                'input_parameters': {
                    'destination_node': n2.hostname,
                    'source_node': n1.hostname,
                    'migration_type': expected_migration_type,
                    'resource_id': instance.uuid,
                    'resource_name': instance.name,
                },
            }
            self.assertEqual(expected, self.strategy.solution.actions[0])
        else:
            self.assertEqual(0, len(self.strategy.solution.actions))

    def test_add_migration_with_active_state(self):
        self._test_add_migration(element.InstanceState.ACTIVE.value)

    def test_add_migration_with_paused_state(self):
        self._test_add_migration(element.InstanceState.PAUSED.value)

    def test_add_migration_with_error_state(self):
        self._test_add_migration(
            element.InstanceState.ERROR.value, expect_migration=False
        )

    def test_add_migration_with_stopped_state(self):
        self._test_add_migration(
            element.InstanceState.STOPPED.value, expected_migration_type="cold"
        )

    def test_is_overloaded(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.is_overloaded(n1, cc)
        self.assertFalse(res)

        cc = {'cpu': 0.025, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.is_overloaded(n1, cc)
        self.assertFalse(res)

        cc = {'cpu': 0.024, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.is_overloaded(n1, cc)
        self.assertTrue(res)

    def test_instance_fits(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n = model.get_node_by_uuid('Node_1')
        instance0 = model.get_instance_by_uuid('INSTANCE_0')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.instance_fits(instance0, n, cc)
        self.assertTrue(res)

        cc = {'cpu': 0.025, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.instance_fits(instance0, n, cc)
        self.assertFalse(res)

    def test_add_action_enable_compute_node(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n = model.get_node_by_uuid('Node_0')
        self.strategy.add_action_enable_compute_node(n)
        expected = [
            {
                'action_type': 'change_nova_service_state',
                'input_parameters': {
                    'state': 'enabled',
                    'resource_id': 'Node_0',
                    'resource_name': 'hostname_0',
                },
            }
        ]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_action_disable_node(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n = model.get_node_by_uuid('Node_0')
        self.strategy.add_action_disable_node(n)
        expected = [
            {
                'action_type': 'change_nova_service_state',
                'input_parameters': {
                    'state': 'disabled',
                    'disabled_reason': 'watcher_disabled',
                    'resource_id': 'Node_0',
                    'resource_name': 'hostname_0',
                },
            }
        ]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_disable_unused_nodes(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        instance_uuid = 'INSTANCE_0'
        instance = model.get_instance_by_uuid(instance_uuid)
        self.strategy.disable_unused_nodes()
        self.assertEqual(0, len(self.strategy.solution.actions))

        # Migrate VM to free the node
        self.strategy.add_migration(instance, n1, n2)

        self.strategy.disable_unused_nodes()
        expected = {
            'action_type': 'change_nova_service_state',
            'input_parameters': {
                'state': 'disabled',
                'disabled_reason': 'watcher_disabled',
                'resource_id': 'Node_0',
                'resource_name': 'hostname_0',
            },
        }
        self.assertEqual(2, len(self.strategy.solution.actions))
        self.assertEqual(expected, self.strategy.solution.actions[1])

    def test_offload_phase(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.offload_phase(cc)
        expected = []
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_consolidation_phase(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        instance_uuid = 'INSTANCE_0'
        instance = model.get_instance_by_uuid(instance_uuid)
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.consolidation_phase(cc)
        expected = [
            {
                'action_type': 'migrate',
                'input_parameters': {
                    'destination_node': n2.hostname,
                    'source_node': n1.hostname,
                    'migration_type': 'live',
                    'resource_id': instance.uuid,
                    'resource_name': instance.name,
                },
            }
        ]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_strategy(self):
        model = self.fake_c_cluster.generate_scenario_2()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model

        result = self.strategy.pre_execute()
        self.assertIsNone(result)

        n1 = model.get_node_by_uuid('Node_0')
        self.strategy.get_relative_cluster_utilization = mock.MagicMock()
        self.strategy.do_execute()

        # Scenario 2 has 6 instances (10 vcpus each) on Node_0 (16 vcpus).
        # Offload moves instances to separate nodes because the allocation
        # check prevents packing more than one 10-vcpu instance on a
        # 16-vcpu node.  Three migrations are needed to bring Node_0's
        # CPU utilization below capacity.  No consolidation is possible
        # and no nodes are left empty.
        actions = self.strategy.solution.actions
        self.assertEqual(3, len(actions))
        for a in actions:
            self.assertEqual('migrate', a['action_type'])
            self.assertEqual(n1.hostname, a['input_parameters']['source_node'])

        compute_nodes_count = len(self.strategy.get_available_compute_nodes())
        number_of_released_nodes = self.strategy.number_of_released_nodes
        number_of_migrations = self.strategy.number_of_migrations
        self.assertEqual(3, number_of_migrations)
        self.assertEqual(0, number_of_released_nodes)
        with mock.patch.object(
            BaseSolution, 'set_efficacy_indicators'
        ) as mock_set_efficacy_indicators:
            result = self.strategy.post_execute()
            mock_set_efficacy_indicators.assert_called_once_with(
                compute_nodes_count=compute_nodes_count,
                released_compute_nodes_count=number_of_released_nodes,
                instance_migrations_count=number_of_migrations,
            )

    def test_strategy2(self):
        model = self.fake_c_cluster.generate_scenario_3()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.offload_phase(cc)
        expected = [
            {
                'action_type': 'migrate',
                'input_parameters': {
                    'destination_node': n2.hostname,
                    'migration_type': 'live',
                    'resource_id': 'INSTANCE_6',
                    'resource_name': '',
                    'source_node': n1.hostname,
                },
            },
            {
                'action_type': 'migrate',
                'input_parameters': {
                    'destination_node': n2.hostname,
                    'migration_type': 'live',
                    'resource_id': 'INSTANCE_7',
                    'resource_name': '',
                    'source_node': n1.hostname,
                },
            },
            {
                'action_type': 'migrate',
                'input_parameters': {
                    'destination_node': n2.hostname,
                    'migration_type': 'live',
                    'resource_id': 'INSTANCE_8',
                    'resource_name': '',
                    'source_node': n1.hostname,
                },
            },
        ]
        self.assertEqual(expected, self.strategy.solution.actions)
        self.strategy.consolidation_phase(cc)
        expected.append(
            {
                'action_type': 'migrate',
                'input_parameters': {
                    'destination_node': n1.hostname,
                    'migration_type': 'live',
                    'resource_id': 'INSTANCE_7',
                    'resource_name': '',
                    'source_node': n2.hostname,
                },
            }
        )
        self.assertEqual(expected, self.strategy.solution.actions)

        cache_before_n1 = self.strategy.node_utilization_cache[
            n1.hostname
        ].copy()
        cache_before_n2 = self.strategy.node_utilization_cache[
            n2.hostname
        ].copy()

        self.strategy.optimize_solution()
        del expected[3]
        del expected[1]
        self.assertEqual(expected, self.strategy.solution.actions)

        cache_after_n1 = self.strategy.node_utilization_cache[n1.hostname]
        cache_after_n2 = self.strategy.node_utilization_cache[n2.hostname]
        # INSTANCE_7 round-trip (Node_0->Node_1->Node_0) was collapsed
        # into a no-op, so cache should remain unchanged.
        for m in ('cpu', 'ram', 'disk'):
            self.assertAlmostEqual(cache_after_n1[m], cache_before_n1[m])
            self.assertAlmostEqual(cache_after_n2[m], cache_before_n2[m])

    def test_strategy_scenario_1(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model

        result = self.strategy.pre_execute()
        self.assertIsNone(result)

        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        self.strategy.get_relative_cluster_utilization = mock.MagicMock()
        self.strategy.do_execute()

        # Scenario 1: 2 nodes (40 vcpus, 64 mem, 250 disk) each with
        # one instance (10 vcpus, 2 mem, 20 disk).  No node is
        # overloaded.  Consolidation moves INSTANCE_0 from the least
        # utilized node (Node_0) to Node_1.  Node_0 is then disabled.
        actions = self.strategy.solution.actions
        expected = [
            {
                'action_type': 'migrate',
                'input_parameters': {
                    'destination_node': n2.hostname,
                    'source_node': n1.hostname,
                    'migration_type': 'live',
                    'resource_id': 'INSTANCE_0',
                    'resource_name': '',
                },
            },
            {
                'action_type': 'change_nova_service_state',
                'input_parameters': {
                    'state': 'disabled',
                    'disabled_reason': 'watcher_disabled',
                    'resource_id': n1.uuid,
                    'resource_name': n1.hostname,
                },
            },
        ]
        self.assertEqual(expected, actions)

        self.assertEqual(1, self.strategy.number_of_migrations)
        self.assertEqual(1, self.strategy.number_of_released_nodes)

        with mock.patch.object(
            BaseSolution, 'set_efficacy_indicators'
        ) as mock_set_efficacy_indicators:
            result = self.strategy.post_execute()
            mock_set_efficacy_indicators.assert_called_once_with(
                compute_nodes_count=2,
                released_compute_nodes_count=1,
                instance_migrations_count=1,
            )

    def test_node_utilization_cache_populated(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")

        self.assertEqual({}, self.strategy.node_utilization_cache)

        result = self.strategy.get_node_utilization(node_0)
        self.assertIn(node_0.hostname, self.strategy.node_utilization_cache)
        cached = self.strategy.node_utilization_cache[node_0.hostname]
        self.assertEqual(result['cpu'], cached['cpu'])
        self.assertEqual(result['ram'], cached['ram'])
        self.assertEqual(result['disk'], cached['disk'])

        result2 = self.strategy.get_node_utilization(node_0)
        self.assertEqual(result, result2)

    def test_node_utilization_cache_updated_after_migration(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_1 = model.get_node_by_uuid("Node_1")

        data_src = self.m_datasource.return_value
        data_src.get_host_cpu_usage = mock.Mock(return_value=30)
        data_src.get_host_ram_usage = mock.Mock(return_value=512 * 1024)

        self.strategy.get_node_utilization(node_0)
        self.strategy.get_node_utilization(node_1)
        before_0 = self.strategy.node_utilization_cache[node_0.hostname]
        before_1 = self.strategy.node_utilization_cache[node_1.hostname]

        instance = model.get_instance_by_uuid('INSTANCE_0')
        instance_util = self.strategy.get_instance_utilization(instance)
        self.strategy.add_migration(instance, node_0, node_1)

        after_0 = self.strategy.node_utilization_cache[node_0.hostname]
        after_1 = self.strategy.node_utilization_cache[node_1.hostname]

        self.assertAlmostEqual(
            after_0['cpu'], before_0['cpu'] - instance_util['cpu']
        )
        self.assertAlmostEqual(
            after_0['ram'], before_0['ram'] - instance_util['ram']
        )
        self.assertAlmostEqual(
            after_0['disk'], before_0['disk'] - instance_util['disk']
        )

        self.assertAlmostEqual(
            after_1['cpu'], before_1['cpu'] + instance_util['cpu']
        )
        self.assertAlmostEqual(
            after_1['ram'], before_1['ram'] + instance_util['ram']
        )
        self.assertAlmostEqual(
            after_1['disk'], before_1['disk'] + instance_util['disk']
        )

    def test_optimize_solution_cache_consistent_after_multihop(self):
        model = self.fake_c_cluster.generate_scenario_2()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_1 = model.get_node_by_uuid("Node_1")
        node_2 = model.get_node_by_uuid("Node_2")

        data_src = self.m_datasource.return_value
        data_src.get_host_cpu_usage = mock.Mock(return_value=30)
        data_src.get_host_ram_usage = mock.Mock(return_value=512 * 1024)

        self.strategy.get_node_utilization(node_0)
        self.strategy.get_node_utilization(node_1)
        self.strategy.get_node_utilization(node_2)

        instance = model.get_instance_by_uuid('INSTANCE_0')
        instance_util = self.strategy.get_instance_utilization(instance)

        before_0 = self.strategy.node_utilization_cache[node_0.hostname].copy()
        before_1 = self.strategy.node_utilization_cache[node_1.hostname].copy()
        before_2 = self.strategy.node_utilization_cache[node_2.hostname].copy()

        self.strategy.add_migration(instance, node_0, node_1)
        self.strategy.add_migration(instance, node_1, node_2)
        self.strategy.optimize_solution()

        after_0 = self.strategy.node_utilization_cache[node_0.hostname]
        after_1 = self.strategy.node_utilization_cache[node_1.hostname]
        after_2 = self.strategy.node_utilization_cache[node_2.hostname]

        for metric in ('cpu', 'ram', 'disk'):
            self.assertAlmostEqual(
                after_0[metric],
                before_0[metric] - instance_util[metric],
                msg="Node_0 (source) used resources should decrease",
            )
            self.assertAlmostEqual(
                after_1[metric],
                before_1[metric],
                msg="Node_1 (intermediate) cache should not change",
            )
            self.assertAlmostEqual(
                after_2[metric],
                before_2[metric] + instance_util[metric],
                msg="Node_2 (destination) used resources should increase",
            )

    def test_instance_fits_allocation_check(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid('INSTANCE_0')
        instance_1 = model.get_instance_by_uuid('INSTANCE_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}

        # Baseline: Node_1 (40 vcpus, 64 mem, 250 disk) hosts
        # INSTANCE_1 (10 vcpus, 2 mem, 20 disk) runs in Node_1
        # INSTANCE_0 (10 vcpus, 2 mem, 20 disk) runs in Node_0 and should fit.
        self.assertTrue(self.strategy.instance_fits(instance_0, node_1, cc))

        # --- vcpu: reject when exhausted ---
        model._node_resource_cache.clear()
        instance_1.vcpus = 35
        self.assertFalse(self.strategy.instance_fits(instance_0, node_1, cc))

        # --- vcpu: accept when just enough ---
        model._node_resource_cache.clear()
        instance_1.vcpus = 30
        self.assertTrue(self.strategy.instance_fits(instance_0, node_1, cc))

        # --- memory: reject when exhausted ---
        model._node_resource_cache.clear()
        instance_1.vcpus = 10
        instance_1.memory = 63
        self.assertFalse(self.strategy.instance_fits(instance_0, node_1, cc))

        # --- memory: accept when just enough ---
        model._node_resource_cache.clear()
        instance_1.memory = 62
        self.assertTrue(self.strategy.instance_fits(instance_0, node_1, cc))

        # --- disk: reject when exhausted ---
        model._node_resource_cache.clear()
        instance_1.memory = 2
        instance_1.disk = 241
        self.assertFalse(self.strategy.instance_fits(instance_0, node_1, cc))

        # --- disk: accept when just enough ---
        model._node_resource_cache.clear()
        instance_1.disk = 230
        self.assertTrue(self.strategy.instance_fits(instance_0, node_1, cc))

    def test_is_node_saturated_not_saturated(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_1 = model.get_node_by_uuid('Node_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        # Scenario_1 memory (64 MB) is below the 128 MB buffer, so
        # seed caches with realistic values: plenty of room left.
        model._node_resource_cache[node_1.uuid] = dict(
            vcpu=10, memory=2048, disk=20
        )
        self.strategy.node_utilization_cache[node_1.hostname] = dict(
            cpu=1.0, ram=1, disk=10
        )
        node_1.memory = 514901
        node_1.memory_mb_reserved = 512
        self.assertFalse(self.strategy.is_node_saturated(node_1, cc))

    def test_is_node_saturated_by_allocation(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_1 = model.get_node_by_uuid('Node_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        # Exhaust vcpu allocation: 40 used on 40 capacity → 0 free.
        model._node_resource_cache[node_1.uuid] = dict(
            vcpu=40, memory=0, disk=0
        )
        self.assertTrue(self.strategy.is_node_saturated(node_1, cc))

    def test_is_node_saturated_by_memory_buffer(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_1 = model.get_node_by_uuid('Node_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        # Leave only 100 MB free memory (below the 128 MB buffer).
        node_1.memory = 514901
        node_1.memory_mb_reserved = 512
        model._node_resource_cache[node_1.uuid] = dict(
            vcpu=0, memory=node_1.memory_mb_capacity - 100, disk=0
        )
        self.strategy.node_utilization_cache[node_1.hostname] = dict(
            cpu=0, ram=0, disk=0
        )
        self.assertTrue(self.strategy.is_node_saturated(node_1, cc))

    def test_is_node_saturated_by_utilization(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_1 = model.get_node_by_uuid('Node_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        # Plenty of allocation room, but CPU utilization at capacity.
        node_1.memory = 514901
        node_1.memory_mb_reserved = 512
        model._node_resource_cache[node_1.uuid] = dict(
            vcpu=10, memory=2048, disk=20
        )
        self.strategy.node_utilization_cache[node_1.hostname] = dict(
            cpu=40.0, ram=0, disk=0
        )
        self.assertTrue(self.strategy.is_node_saturated(node_1, cc))
