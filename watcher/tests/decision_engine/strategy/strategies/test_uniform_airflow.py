# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel Corp
#
# Authors: Junjie-Huang <junjie.huang@intel.com>
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
import collections
from unittest import mock

from watcher.applier.loading import default
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.model import ceilometer_metrics
from watcher.tests.decision_engine.model import gnocchi_metrics
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestUniformAirflow(TestBaseStrategy):

    scenarios = [
        ("Ceilometer",
         {"datasource": "ceilometer",
          "fake_datasource_cls": ceilometer_metrics.FakeCeilometerMetrics}),
        ("Gnocchi",
         {"datasource": "gnocchi",
          "fake_datasource_cls": gnocchi_metrics.FakeGnocchiMetrics}),
    ]

    def setUp(self):
        super(TestUniformAirflow, self).setUp()
        # fake metrics
        self.fake_metrics = self.fake_datasource_cls()

        p_datasource = mock.patch.object(
            strategies.UniformAirflow, 'datasource_backend',
            new_callable=mock.PropertyMock)
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        self.m_datasource.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics,
            NAME=self.fake_metrics.NAME)
        self.strategy = strategies.UniformAirflow(
            config=mock.Mock(datasource=self.datasource))
        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update({'threshold_airflow': 400.0,
                                               'threshold_inlet_t': 28.0,
                                               'threshold_power': 350.0,
                                               'period': 300})
        self.strategy.threshold_airflow = 400
        self.strategy.threshold_inlet_t = 28
        self.strategy.threshold_power = 350
        self._period = 300
        self.strategy.pre_execute()

    def test_calc_used_resource(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        node = model.get_node_by_uuid('Node_0')
        cores_used, mem_used, disk_used = (
            self.strategy.calculate_used_resource(node))
        self.assertEqual((cores_used, mem_used, disk_used), (25, 4, 40))

    def test_group_hosts_by_airflow(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        self.strategy.threshold_airflow = 300
        n1, n2 = self.strategy.group_hosts_by_airflow()
        # print n1, n2, avg, w_map
        self.assertEqual(n1[0]['node'].uuid, 'Node_0')
        self.assertEqual(n2[0]['node'].uuid, 'Node_1')

    def test_choose_instance_to_migrate(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 22
        n1, n2 = self.strategy.group_hosts_by_airflow()
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)

        self.assertEqual(instance_to_mig[0].uuid, 'Node_0')
        self.assertEqual(len(instance_to_mig[1]), 1)
        self.assertIn(instance_to_mig[1][0].uuid,
                      {'cae81432-1631-4d4e-b29c-6f3acdcde906',
                       '73b09e16-35b7-4922-804e-e8f5d9b740fc'})

    def test_choose_instance_to_migrate_all(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 25
        n1, n2 = self.strategy.group_hosts_by_airflow()
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)

        self.assertEqual(instance_to_mig[0].uuid, 'Node_0')
        self.assertEqual(len(instance_to_mig[1]), 2)
        self.assertEqual({'cae81432-1631-4d4e-b29c-6f3acdcde906',
                          '73b09e16-35b7-4922-804e-e8f5d9b740fc'},
                         {inst.uuid for inst in instance_to_mig[1]})

    def test_choose_instance_notfound(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 22
        n1, n2 = self.strategy.group_hosts_by_airflow()
        instances = model.get_all_instances()
        [model.remove_instance(inst) for inst in instances.values()]
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)
        self.assertIsNone(instance_to_mig)

    def test_filter_destination_hosts(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 22
        n1, n2 = self.strategy.group_hosts_by_airflow()
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)
        dest_hosts = self.strategy.filter_destination_hosts(
            n2, instance_to_mig[1])

        self.assertEqual(len(dest_hosts), 1)
        self.assertEqual(dest_hosts[0]['node'].uuid, 'Node_1')
        self.assertIn(instance_to_mig[1][0].uuid,
                      {'cae81432-1631-4d4e-b29c-6f3acdcde906',
                       '73b09e16-35b7-4922-804e-e8f5d9b740fc'})

    def test_execute_no_workload(self):
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 25
        self.strategy.threshold_power = 300
        model = self.fake_c_cluster.\
            generate_scenario_4_with_1_node_no_instance()
        self.m_c_model.return_value = model
        solution = self.strategy.execute()
        self.assertEqual([], solution.actions)

    def test_execute(self):
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 25
        self.strategy.threshold_power = 300
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        solution = self.strategy.execute()
        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        num_migrations = actions_counter.get("migrate", 0)
        self.assertEqual(num_migrations, 2)

    def test_check_parameters(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
