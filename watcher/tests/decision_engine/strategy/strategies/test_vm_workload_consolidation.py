# -*- encoding: utf-8 -*-
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
from watcher.tests.decision_engine.model import faker_cluster_and_metrics
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestVMWorkloadConsolidation(TestBaseStrategy):

    scenarios = [
        ("Ceilometer",
         {"datasource": "ceilometer",
          "fake_datasource_cls":
          faker_cluster_and_metrics.FakeCeilometerMetrics}),
        ("Gnocchi",
         {"datasource": "gnocchi",
          "fake_datasource_cls":
          faker_cluster_and_metrics.FakeGnocchiMetrics}),
    ]

    def setUp(self):
        super(TestVMWorkloadConsolidation, self).setUp()

        # fake cluster
        self.fake_c_cluster = faker_cluster_and_metrics.FakerModelCollector()

        p_datasource = mock.patch.object(
            strategies.VMWorkloadConsolidation, 'datasource_backend',
            new_callable=mock.PropertyMock)
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        # fake metrics
        self.fake_metrics = self.fake_datasource_cls(
            self.m_c_model.return_value)

        self.m_datasource.return_value = mock.Mock(
            get_instance_cpu_usage=(
                self.fake_metrics.get_instance_cpu_util),
            get_instance_ram_usage=(
                self.fake_metrics.get_instance_ram_util),
            get_instance_root_disk_size=(
                self.fake_metrics.get_instance_disk_root_size),
            )
        self.strategy = strategies.VMWorkloadConsolidation(
            config=mock.Mock(datasources=self.datasource))

    def test_get_instance_utilization(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_util = dict(cpu=1.0, ram=1, disk=10)
        self.assertEqual(
            instance_util,
            self.strategy.get_instance_utilization(instance_0))

    def test_get_node_utilization(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_util = dict(cpu=1.0, ram=1, disk=10)
        self.assertEqual(
            node_util,
            self.strategy.get_node_utilization(node_0))

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

    def test_add_migration_with_active_state(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        instance_uuid = 'INSTANCE_0'
        instance = model.get_instance_by_uuid(instance_uuid)
        self.strategy.add_migration(instance, n1, n2)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = {'action_type': 'migrate',
                    'input_parameters': {'destination_node': n2.hostname,
                                         'source_node': n1.hostname,
                                         'migration_type': 'live',
                                         'resource_id': instance.uuid,
                                         'resource_name': instance.name}}
        self.assertEqual(expected, self.strategy.solution.actions[0])

    def test_add_migration_with_paused_state(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        instance_uuid = 'INSTANCE_0'
        instance = model.get_instance_by_uuid(instance_uuid)
        setattr(instance, 'state', element.InstanceState.ERROR.value)
        self.strategy.add_migration(instance, n1, n2)
        self.assertEqual(0, len(self.strategy.solution.actions))

        setattr(instance, 'state', element.InstanceState.PAUSED.value)
        self.strategy.add_migration(instance, n1, n2)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = {'action_type': 'migrate',
                    'input_parameters': {'destination_node': n2.hostname,
                                         'source_node': n1.hostname,
                                         'migration_type': 'live',
                                         'resource_id': instance.uuid,
                                         'resource_name': instance.name}}
        self.assertEqual(expected, self.strategy.solution.actions[0])

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
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {'state': 'enabled',
                                          'resource_id': 'Node_0',
                                          'resource_name': 'hostname_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_action_disable_node(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n = model.get_node_by_uuid('Node_0')
        self.strategy.add_action_disable_node(n)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'state': 'disabled',
                         'disabled_reason': 'watcher_disabled',
                         'resource_id': 'Node_0',
                         'resource_name': 'hostname_0'}}]
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
        expected = {'action_type': 'change_nova_service_state',
                    'input_parameters': {
                        'state': 'disabled',
                        'disabled_reason': 'watcher_disabled',
                        'resource_id': 'Node_0',
                        'resource_name': 'hostname_0'}}
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
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'destination_node': n2.hostname,
                                          'source_node': n1.hostname,
                                          'migration_type': 'live',
                                          'resource_id': instance.uuid,
                                          'resource_name': instance.name}}]
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
        n2_name = self.strategy.solution.actions[0][
            'input_parameters']['destination_node']
        n2 = model.get_node_by_name(n2_name)
        n3_uuid = self.strategy.solution.actions[2][
            'input_parameters']['resource_id']
        n3 = model.get_node_by_uuid(n3_uuid)
        n4_uuid = self.strategy.solution.actions[3][
            'input_parameters']['resource_id']
        n4 = model.get_node_by_uuid(n4_uuid)
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'destination_node': n2.hostname,
                                          'source_node': n1.hostname,
                                          'migration_type': 'live',
                                          'resource_id': 'INSTANCE_3',
                                          'resource_name': ''}},
                    {'action_type': 'migrate',
                     'input_parameters': {'destination_node': n2.hostname,
                                          'source_node': n1.hostname,
                                          'migration_type': 'live',
                                          'resource_id': 'INSTANCE_1',
                                          'resource_name': ''}},
                    {'action_type': 'change_nova_service_state',
                     'input_parameters': {'state': 'disabled',
                                          'disabled_reason':
                                          'watcher_disabled',
                                          'resource_id': n3.uuid,
                                          'resource_name': n3.hostname}},
                    {'action_type': 'change_nova_service_state',
                     'input_parameters': {'state': 'disabled',
                                          'disabled_reason':
                                          'watcher_disabled',
                                          'resource_id': n4.uuid,
                                          'resource_name': n4.hostname}}]
        self.assertEqual(expected, self.strategy.solution.actions)

        compute_nodes_count = len(self.strategy.get_available_compute_nodes())
        number_of_released_nodes = self.strategy.number_of_released_nodes
        number_of_migrations = self.strategy.number_of_migrations
        with mock.patch.object(
            BaseSolution, 'set_efficacy_indicators'
        ) as mock_set_efficacy_indicators:
            result = self.strategy.post_execute()
            mock_set_efficacy_indicators.assert_called_once_with(
                compute_nodes_count=compute_nodes_count,
                released_compute_nodes_count=number_of_released_nodes,
                instance_migrations_count=number_of_migrations
            )

    def test_strategy2(self):
        model = self.fake_c_cluster.generate_scenario_3()
        self.m_c_model.return_value = model
        self.fake_metrics.model = model
        n1 = model.get_node_by_uuid('Node_0')
        n2 = model.get_node_by_uuid('Node_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.offload_phase(cc)
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'destination_node': n2.hostname,
                                          'migration_type': 'live',
                                          'resource_id': 'INSTANCE_6',
                                          'resource_name': '',
                                          'source_node': n1.hostname}},
                    {'action_type': 'migrate',
                     'input_parameters': {'destination_node': n2.hostname,
                                          'migration_type': 'live',
                                          'resource_id': 'INSTANCE_7',
                                          'resource_name': '',
                                          'source_node': n1.hostname}},
                    {'action_type': 'migrate',
                     'input_parameters': {'destination_node': n2.hostname,
                                          'migration_type': 'live',
                                          'resource_id': 'INSTANCE_8',
                                          'resource_name': '',
                                          'source_node': n1.hostname}}]
        self.assertEqual(expected, self.strategy.solution.actions)
        self.strategy.consolidation_phase(cc)
        expected.append({'action_type': 'migrate',
                         'input_parameters': {'destination_node': n1.hostname,
                                              'migration_type': 'live',
                                              'resource_id': 'INSTANCE_7',
                                              'resource_name': '',
                                              'source_node': n2.hostname}})
        self.assertEqual(expected, self.strategy.solution.actions)
        self.strategy.optimize_solution()
        del expected[3]
        del expected[1]
        self.assertEqual(expected, self.strategy.solution.actions)
