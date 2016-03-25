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

from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies \
    import faker_metrics_collector


class TestWorkloadStabilization(base.BaseTestCase):
    # fake metrics
    fake_metrics = faker_metrics_collector.FakerMetricsCollector()

    # fake cluster
    fake_cluster = faker_cluster_state.FakerModelCollector()

    hosts_load_assert = {'Node_0':
                         {'cpu_util': 7.0, 'memory.resident': 7.0,
                          'vcpus': 40},
                         'Node_1':
                         {'cpu_util': 5.0, 'memory.resident': 5,
                          'vcpus': 40},
                         'Node_2':
                         {'cpu_util': 10.0, 'memory.resident': 29,
                          'vcpus': 40},
                         'Node_3':
                         {'cpu_util': 4.0, 'memory.resident': 8,
                          'vcpus': 40},
                         'Node_4':
                         {'cpu_util': 2.0, 'memory.resident': 4,
                          'vcpus': 40}}

    def test_get_vm_load(self):
        model = self.fake_cluster.generate_scenario_1()
        sd = strategies.WorkloadStabilization()
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        vm_0_dict = {'uuid': 'VM_0', 'vcpus': 10,
                     'cpu_util': 7, 'memory.resident': 2}
        self.assertEqual(sd.get_vm_load("VM_0", model), vm_0_dict)

    def test_normalize_hosts_load(self):
        model = self.fake_cluster.generate_scenario_1()
        sd = strategies.WorkloadStabilization()
        fake_hosts = {'Node_0': {'cpu_util': 7.0, 'memory.resident': 7},
                      'Node_1': {'cpu_util': 5.0, 'memory.resident': 5}}
        normalized_hosts = {'Node_0':
                            {'cpu_util': 0.07,
                             'memory.resident': 0.05303030303030303},
                            'Node_1':
                            {'cpu_util': 0.05,
                             'memory.resident': 0.03787878787878788}}
        self.assertEqual(sd.normalize_hosts_load(fake_hosts, model),
                         normalized_hosts)

    def test_get_hosts_load(self):
        sd = strategies.WorkloadStabilization()
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.assertEqual(
            sd.get_hosts_load(self.fake_cluster.generate_scenario_1()),
            self.hosts_load_assert)

    def test_get_sd(self):
        sd = strategies.WorkloadStabilization()
        test_cpu_sd = 2.7
        test_ram_sd = 9.3
        self.assertEqual(
            round(sd.get_sd(self.hosts_load_assert, 'cpu_util'), 1),
            test_cpu_sd)
        self.assertEqual(
            round(sd.get_sd(self.hosts_load_assert, 'memory.resident'), 1),
            test_ram_sd)

    def test_calculate_weighted_sd(self):
        sd = strategies.WorkloadStabilization()
        sd_case = [0.5, 0.75]
        self.assertEqual(sd.calculate_weighted_sd(sd_case), 1.25)

    def test_calculate_migration_case(self):
        model = self.fake_cluster.generate_scenario_1()
        sd = strategies.WorkloadStabilization()
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.assertEqual(sd.calculate_migration_case(
            self.hosts_load_assert, "VM_5", "Node_2", "Node_1",
            model)[-1]["Node_1"],
            {'cpu_util': 7.5, 'memory.resident': 21, 'vcpus': 40})

    def test_simulate_migrations(self):
        sd = strategies.WorkloadStabilization()
        sd.host_choice = 'retry'
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.assertEqual(
            len(sd.simulate_migrations(self.fake_cluster.generate_scenario_1(),
                                       self.hosts_load_assert)),
            8)

    def test_check_threshold(self):
        sd = strategies.WorkloadStabilization()
        sd.thresholds = {'cpu_util': 0.001, 'memory.resident': 0.2}
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        sd.simulate_migrations = mock.Mock(return_value=True)
        self.assertTrue(
            sd.check_threshold(self.fake_cluster.generate_scenario_1()))

    def test_execute_one_migration(self):
        sd = strategies.WorkloadStabilization()
        model = self.fake_cluster.generate_scenario_1()
        sd.thresholds = {'cpu_util': 0.001, 'memory.resident': 0.2}
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        sd.simulate_migrations = mock.Mock(return_value=[{'vm': 'VM_4',
                                                          's_host': 'Node_2',
                                                          'host': 'Node_1'}])
        with mock.patch.object(sd, 'migrate') as mock_migration:
            sd.execute(model)
            mock_migration.assert_called_once_with(model, 'VM_4', 'Node_2',
                                                   'Node_1')

    def test_execute_multiply_migrations(self):
        sd = strategies.WorkloadStabilization()
        model = self.fake_cluster.generate_scenario_1()
        sd.thresholds = {'cpu_util': 0.022, 'memory.resident': 0.0001}
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        sd.simulate_migrations = mock.Mock(return_value=[{'vm': 'VM_4',
                                                          's_host': 'Node_2',
                                                          'host': 'Node_1'},
                                                         {'vm': 'VM_3',
                                                          's_host': 'Node_2',
                                                          'host': 'Node_3'}])
        with mock.patch.object(sd, 'migrate') as mock_migrate:
            sd.execute(model)
            self.assertEqual(mock_migrate.call_count, 2)

    def test_execute_nothing_to_migrate(self):
        sd = strategies.WorkloadStabilization()
        model = self.fake_cluster.generate_scenario_1()
        sd.thresholds = {'cpu_util': 0.042, 'memory.resident': 0.0001}
        sd.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        sd.simulate_migrations = mock.Mock(return_value=False)
        with mock.patch.object(sd, 'migrate') as mock_migrate:
            sd.execute(model)
            mock_migrate.assert_not_called()
