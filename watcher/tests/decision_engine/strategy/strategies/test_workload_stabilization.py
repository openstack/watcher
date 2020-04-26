# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica LLC
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
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

from watcher.common import clients
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.model import ceilometer_metrics
from watcher.tests.decision_engine.model import gnocchi_metrics
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestWorkloadStabilization(TestBaseStrategy):

    scenarios = [
        ("Ceilometer",
         {"datasource": "ceilometer",
          "fake_datasource_cls": ceilometer_metrics.FakeCeilometerMetrics}),
        ("Gnocchi",
         {"datasource": "gnocchi",
          "fake_datasource_cls": gnocchi_metrics.FakeGnocchiMetrics}),
    ]

    def setUp(self):
        super(TestWorkloadStabilization, self).setUp()

        # fake metrics
        self.fake_metrics = self.fake_datasource_cls()

        self.hosts_load_assert = {
            'Node_0': {'instance_cpu_usage': 0.07,
                       'instance_ram_usage': 7.0, 'vcpus': 40},
            'Node_1': {'instance_cpu_usage': 0.07,
                       'instance_ram_usage': 5, 'vcpus': 40},
            'Node_2': {'instance_cpu_usage': 0.8,
                       'instance_ram_usage': 29, 'vcpus': 40},
            'Node_3': {'instance_cpu_usage': 0.05,
                       'instance_ram_usage': 8, 'vcpus': 40},
            'Node_4': {'instance_cpu_usage': 0.05,
                       'instance_ram_usage': 4, 'vcpus': 40}}

        p_osc = mock.patch.object(
            clients, "OpenStackClients")
        self.m_osc = p_osc.start()
        self.addCleanup(p_osc.stop)

        p_datasource = mock.patch.object(
            strategies.WorkloadStabilization, "datasource_backend",
            new_callable=mock.PropertyMock)
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        self.m_datasource.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        self.strategy = strategies.WorkloadStabilization(
            config=mock.Mock(datasource=self.datasource))
        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update(
            {'metrics': ["instance_cpu_usage", "instance_ram_usage"],
             'thresholds': {"instance_cpu_usage": 0.2,
                            "instance_ram_usage": 0.2},
             'weights': {"instance_cpu_usage_weight": 1.0,
                         "instance_ram_usage_weight": 1.0},
             'instance_metrics':
                 {"instance_cpu_usage": "host_cpu_usage",
                  "instance_ram_usage": "host_ram_usage"},
             'host_choice': 'retry',
             'retry_count': 1,
             'periods': {
                 "instance": 720,
                 "compute_node": 600,
                 "node": 0},
             'aggregation_method': {
                 "instance": "mean",
                 "compute_node": "mean",
                 "node": ''}})
        self.strategy.metrics = ["instance_cpu_usage", "instance_ram_usage"]
        self.strategy.thresholds = {"instance_cpu_usage": 0.2,
                                    "instance_ram_usage": 0.2}
        self.strategy.weights = {"instance_cpu_usage_weight": 1.0,
                                 "instance_ram_usage_weight": 1.0}
        self.strategy.instance_metrics = {
            "instance_cpu_usage": "host_cpu_usage",
            "instance_ram_usage": "host_ram_usage"}
        self.strategy.host_choice = 'retry'
        self.strategy.retry_count = 1
        self.strategy.periods = {
            "instance": 720,
            "compute_node": 600,
            # node is deprecated
            "node": 0,
        }
        self.strategy.aggregation_method = {
            "instance": "mean",
            "compute_node": "mean",
            # node is deprecated
            "node": '',
        }

    def test_get_instance_load(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        instance0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_0_dict = {
            'uuid': 'INSTANCE_0', 'vcpus': 10,
            'instance_cpu_usage': 0.07, 'instance_ram_usage': 2}
        self.assertEqual(
            instance_0_dict, self.strategy.get_instance_load(instance0))

    def test_get_instance_load_with_no_metrics(self):
        model = self.fake_c_cluster.\
            generate_scenario_1_with_1_node_unavailable()
        self.m_c_model.return_value = model
        lost_instance = model.get_instance_by_uuid("LOST_INSTANCE")
        self.assertIsNone(self.strategy.get_instance_load(lost_instance))

    def test_normalize_hosts_load(self):
        self.m_c_model.return_value = self.fake_c_cluster.generate_scenario_1()
        fake_hosts = {'Node_0': {'instance_cpu_usage': 0.07,
                                 'instance_ram_usage': 7},
                      'Node_1': {'instance_cpu_usage': 0.05,
                                 'instance_ram_usage': 5}}
        normalized_hosts = {'Node_0':
                            {'instance_cpu_usage': 0.07,
                             'instance_ram_usage': 0.05303030303030303},
                            'Node_1':
                            {'instance_cpu_usage': 0.05,
                             'instance_ram_usage': 0.03787878787878788}}
        self.assertEqual(
            normalized_hosts,
            self.strategy.normalize_hosts_load(fake_hosts))

    def test_get_available_nodes(self):
        self.m_c_model.return_value = self.fake_c_cluster. \
            generate_scenario_9_with_3_active_plus_1_disabled_nodes()
        self.assertEqual(3, len(self.strategy.get_available_nodes()))

    def test_get_hosts_load(self):
        self.m_c_model.return_value = self.fake_c_cluster.\
            generate_scenario_1()
        self.assertEqual(self.strategy.get_hosts_load(),
                         self.hosts_load_assert)

    def test_get_hosts_load_with_node_missing(self):
        self.m_c_model.return_value = \
            self.fake_c_cluster.\
            generate_scenario_1_with_1_node_unavailable()
        self.assertEqual(self.hosts_load_assert,
                         self.strategy.get_hosts_load())

    def test_get_sd(self):
        test_cpu_sd = 0.296
        test_ram_sd = 9.3
        self.assertEqual(
            round(self.strategy.get_sd(
                self.hosts_load_assert, 'instance_cpu_usage'), 3),
            test_cpu_sd)
        self.assertEqual(
            round(self.strategy.get_sd(
                self.hosts_load_assert, 'instance_ram_usage'), 1),
            test_ram_sd)

    def test_calculate_weighted_sd(self):
        sd_case = [0.5, 0.75]
        self.assertEqual(self.strategy.calculate_weighted_sd(sd_case), 1.25)

    def test_calculate_migration_case(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        instance = model.get_instance_by_uuid("INSTANCE_5")
        src_node = model.get_node_by_uuid("Node_2")
        dst_node = model.get_node_by_uuid("Node_1")
        result = self.strategy.calculate_migration_case(
            self.hosts_load_assert, instance,
            src_node, dst_node)[-1][dst_node.uuid]
        result['instance_cpu_usage'] = round(result['instance_cpu_usage'], 3)
        self.assertEqual(result, {'instance_cpu_usage': 0.095,
                                  'instance_ram_usage': 21.0,
                                  'vcpus': 40})

    def test_simulate_migrations(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        self.strategy.host_choice = 'fullsearch'
        self.assertEqual(
            10,
            len(self.strategy.simulate_migrations(self.hosts_load_assert)))

    def test_simulate_migrations_with_all_instances_exclude(self):
        model = \
            self.fake_c_cluster.\
            generate_scenario_1_with_all_instances_exclude()
        self.m_c_model.return_value = model
        self.strategy.host_choice = 'fullsearch'
        self.assertEqual(
            0,
            len(self.strategy.simulate_migrations(self.hosts_load_assert)))

    def test_check_threshold(self):
        self.m_c_model.return_value = self.fake_c_cluster.generate_scenario_1()
        self.strategy.thresholds = {'instance_cpu_usage': 0.001,
                                    'instance_ram_usage': 0.2}
        self.strategy.simulate_migrations = mock.Mock(return_value=True)
        self.assertTrue(self.strategy.check_threshold())

    def test_execute_one_migration(self):
        self.m_c_model.return_value = self.fake_c_cluster.generate_scenario_1()
        self.strategy.thresholds = {'instance_cpu_usage': 0.001,
                                    'instance_ram_usage': 0.2}
        self.strategy.simulate_migrations = mock.Mock(
            return_value=[
                {'instance': 'INSTANCE_4', 's_host': 'Node_2',
                 'host': 'Node_1'}]
        )
        with mock.patch.object(self.strategy, 'migrate') as mock_migration:
            self.strategy.do_execute()
            mock_migration.assert_called_once_with(
                'INSTANCE_4', 'Node_2', 'Node_1')

    def test_execute_multiply_migrations(self):
        self.m_c_model.return_value = self.fake_c_cluster.generate_scenario_1()
        self.strategy.thresholds = {'instance_cpu_usage': 0.00001,
                                    'instance_ram_usage': 0.0001}
        self.strategy.simulate_migrations = mock.Mock(
            return_value=[
                {'instance': 'INSTANCE_4', 's_host': 'Node_2',
                 'host': 'Node_1'},
                {'instance': 'INSTANCE_3', 's_host': 'Node_2',
                 'host': 'Node_3'}]
        )
        with mock.patch.object(self.strategy, 'migrate') as mock_migrate:
            self.strategy.do_execute()
            self.assertEqual(mock_migrate.call_count, 2)

    def test_execute_nothing_to_migrate(self):
        self.m_c_model.return_value = self.fake_c_cluster.generate_scenario_1()
        self.strategy.thresholds = {'instance_cpu_usage': 0.042,
                                    'instance_ram_usage': 0.0001}
        self.strategy.simulate_migrations = mock.Mock(return_value=False)
        self.strategy.instance_migrations_count = 0
        with mock.patch.object(self.strategy, 'migrate') as mock_migrate:
            self.strategy.execute()
            mock_migrate.assert_not_called()

    def test_parameter_backwards_compat(self):
        # Set the deprecated node values to a none default value
        self.strategy.input_parameters.update(
            {'periods': {
                "instance": 720,
                "compute_node": 600,
                "node": 500
            }, 'aggregation_method': {
                "instance": "mean",
                "compute_node": "mean",
                "node": 'min'}})

        # Pre execute method handles backwards compatibility of parameters
        self.strategy.pre_execute()

        # assert that the compute_node values are updated to the those of node
        self.assertEqual(
            'min', self.strategy.aggregation_method['compute_node'])
        self.assertEqual(
            500, self.strategy.periods['compute_node'])
