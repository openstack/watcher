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

import mock

from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies \
    import faker_metrics_collector


class TestWorkloadStabilization(base.BaseTestCase):

    def setUp(self):
        super(TestWorkloadStabilization, self).setUp()

        # fake metrics
        self.fake_metrics = faker_metrics_collector.FakerMetricsCollector()

        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        self.hosts_load_assert = {
            'Node_0': {'cpu_util': 0.07, 'memory.resident': 7.0, 'vcpus': 40},
            'Node_1': {'cpu_util': 0.05, 'memory.resident': 5, 'vcpus': 40},
            'Node_2': {'cpu_util': 0.1, 'memory.resident': 29, 'vcpus': 40},
            'Node_3': {'cpu_util': 0.04, 'memory.resident': 8, 'vcpus': 40},
            'Node_4': {'cpu_util': 0.02, 'memory.resident': 4, 'vcpus': 40}}

        p_model = mock.patch.object(
            strategies.WorkloadStabilization, "model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_ceilometer = mock.patch.object(
            strategies.WorkloadStabilization, "ceilometer",
            new_callable=mock.PropertyMock)
        self.m_ceilometer = p_ceilometer.start()
        self.addCleanup(p_ceilometer.stop)

        self.m_model.return_value = model_root.ModelRoot()
        self.m_ceilometer.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.strategy = strategies.WorkloadStabilization(config=mock.Mock())

    def test_get_vm_load(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        vm_0_dict = {'uuid': 'VM_0', 'vcpus': 10,
                     'cpu_util': 7, 'memory.resident': 2}
        self.assertEqual(vm_0_dict, self.strategy.get_vm_load("VM_0"))

    def test_normalize_hosts_load(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        fake_hosts = {'Node_0': {'cpu_util': 0.07, 'memory.resident': 7},
                      'Node_1': {'cpu_util': 0.05, 'memory.resident': 5}}
        normalized_hosts = {'Node_0':
                            {'cpu_util': 0.07,
                             'memory.resident': 0.05303030303030303},
                            'Node_1':
                            {'cpu_util': 0.05,
                             'memory.resident': 0.03787878787878788}}
        self.assertEqual(
            normalized_hosts,
            self.strategy.normalize_hosts_load(fake_hosts))

    def test_get_hosts_load(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        self.assertEqual(
            self.strategy.get_hosts_load(),
            self.hosts_load_assert)

    def test_get_sd(self):
        test_cpu_sd = 0.027
        test_ram_sd = 9.3
        self.assertEqual(
            round(self.strategy.get_sd(
                self.hosts_load_assert, 'cpu_util'), 3),
            test_cpu_sd)
        self.assertEqual(
            round(self.strategy.get_sd(
                self.hosts_load_assert, 'memory.resident'), 1),
            test_ram_sd)

    def test_calculate_weighted_sd(self):
        sd_case = [0.5, 0.75]
        self.assertEqual(self.strategy.calculate_weighted_sd(sd_case), 1.25)

    def test_calculate_migration_case(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        self.assertEqual(
            self.strategy.calculate_migration_case(
                self.hosts_load_assert, "VM_5",
                "Node_2", "Node_1")[-1]["Node_1"],
            {'cpu_util': 2.55, 'memory.resident': 21, 'vcpus': 40})

    def test_simulate_migrations(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.strategy.host_choice = 'retry'
        self.assertEqual(
            8,
            len(self.strategy.simulate_migrations(self.hosts_load_assert)))

    def test_check_threshold(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        self.strategy.thresholds = {'cpu_util': 0.001, 'memory.resident': 0.2}
        self.strategy.simulate_migrations = mock.Mock(return_value=True)
        self.assertTrue(self.strategy.check_threshold())

    def test_execute_one_migration(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        self.strategy.thresholds = {'cpu_util': 0.001, 'memory.resident': 0.2}
        self.strategy.simulate_migrations = mock.Mock(
            return_value=[{'vm': 'VM_4', 's_host': 'Node_2', 'host': 'Node_1'}]
        )
        with mock.patch.object(self.strategy, 'migrate') as mock_migration:
            self.strategy.execute()
            mock_migration.assert_called_once_with(
                'VM_4', 'Node_2', 'Node_1')

    def test_execute_multiply_migrations(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        self.strategy.thresholds = {'cpu_util': 0.00001,
                                    'memory.resident': 0.0001}
        self.strategy.simulate_migrations = mock.Mock(
            return_value=[{'vm': 'VM_4', 's_host': 'Node_2', 'host': 'Node_1'},
                          {'vm': 'VM_3', 's_host': 'Node_2', 'host': 'Node_3'}]
        )
        with mock.patch.object(self.strategy, 'migrate') as mock_migrate:
            self.strategy.execute()
            self.assertEqual(mock_migrate.call_count, 1)

    def test_execute_nothing_to_migrate(self):
        self.m_model.return_value = self.fake_cluster.generate_scenario_1()
        self.strategy.thresholds = {'cpu_util': 0.042,
                                    'memory.resident': 0.0001}
        self.strategy.simulate_migrations = mock.Mock(return_value=False)
        with mock.patch.object(self.strategy, 'migrate') as mock_migrate:
            self.strategy.execute()
            mock_migrate.assert_not_called()
