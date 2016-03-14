# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
import mock

from watcher.applier.actions.loading import default
from watcher.common import exception
from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies \
    import faker_metrics_collector


class TestBasicConsolidation(base.BaseTestCase):
    # fake metrics
    fake_metrics = faker_metrics_collector.FakerMetricsCollector()

    # fake cluster
    fake_cluster = faker_cluster_state.FakerModelCollector()

    def test_cluster_size(self):
        size_cluster = len(
            self.fake_cluster.generate_scenario_1().get_all_hypervisors())
        size_cluster_assert = 5
        self.assertEqual(size_cluster_assert, size_cluster)

    def test_basic_consolidation_score_hypervisor(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        node_1_score = 0.023333333333333317
        self.assertEqual(node_1_score, sercon.calculate_score_node(
            cluster.get_hypervisor_from_id("Node_1"),
            cluster))
        node_2_score = 0.26666666666666666
        self.assertEqual(node_2_score, sercon.calculate_score_node(
            cluster.get_hypervisor_from_id("Node_2"),
            cluster))
        node_0_score = 0.023333333333333317
        self.assertEqual(node_0_score, sercon.calculate_score_node(
            cluster.get_hypervisor_from_id("Node_0"),
            cluster))

    def test_basic_consolidation_score_vm(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        vm_0 = cluster.get_vm_from_id("VM_0")
        vm_0_score = 0.023333333333333317
        self.assertEqual(vm_0_score, sercon.calculate_score_vm(vm_0, cluster))

        vm_1 = cluster.get_vm_from_id("VM_1")
        vm_1_score = 0.023333333333333317
        self.assertEqual(vm_1_score, sercon.calculate_score_vm(vm_1, cluster))
        vm_2 = cluster.get_vm_from_id("VM_2")
        vm_2_score = 0.033333333333333326
        self.assertEqual(vm_2_score, sercon.calculate_score_vm(vm_2, cluster))
        vm_6 = cluster.get_vm_from_id("VM_6")
        vm_6_score = 0.02666666666666669
        self.assertEqual(vm_6_score, sercon.calculate_score_vm(vm_6, cluster))
        vm_7 = cluster.get_vm_from_id("VM_7")
        vm_7_score = 0.013333333333333345
        self.assertEqual(vm_7_score, sercon.calculate_score_vm(vm_7, cluster))

    def test_basic_consolidation_score_vm_disk(self):
        cluster = self.fake_cluster.generate_scenario_5_with_vm_disk_0()
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        vm_0 = cluster.get_vm_from_id("VM_0")
        vm_0_score = 0.023333333333333355
        self.assertEqual(vm_0_score, sercon.calculate_score_vm(vm_0, cluster))

    def test_basic_consolidation_weight(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        vm_0 = cluster.get_vm_from_id("VM_0")
        cores = 16
        # 80 Go
        disk = 80
        # mem 8 Go
        mem = 8
        vm_0_weight_assert = 3.1999999999999997
        self.assertEqual(vm_0_weight_assert,
                         sercon.calculate_weight(cluster, vm_0, cores, disk,
                                                 mem))

    def test_calculate_migration_efficacy(self):
        sercon = strategies.BasicConsolidation()
        sercon.calculate_migration_efficacy()

    def test_exception_model(self):
        sercon = strategies.BasicConsolidation()
        self.assertRaises(exception.ClusterStateNotDefined, sercon.execute,
                          None)

    def test_exception_cluster_empty(self):
        sercon = strategies.BasicConsolidation()
        model = model_root.ModelRoot()
        self.assertRaises(exception.ClusterEmpty, sercon.execute,
                          model)

    def test_calculate_score_vm_raise_cluster_state_not_found(self):
        metrics = faker_metrics_collector.FakerMetricsCollector()
        metrics.empty_one_metric("CPU_COMPUTE")
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        self.assertRaises(exception.ClusterStateNotDefined,
                          sercon.calculate_score_vm, "VM_1", None)

    def test_check_migration(self):
        sercon = strategies.BasicConsolidation()
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()

        all_vms = model.get_all_vms()
        all_hyps = model.get_all_hypervisors()
        vm0 = all_vms[list(all_vms.keys())[0]]
        hyp0 = all_hyps[list(all_hyps.keys())[0]]

        sercon.check_migration(model, hyp0, hyp0, vm0)

    def test_threshold(self):
        sercon = strategies.BasicConsolidation()
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()

        all_hyps = model.get_all_hypervisors()
        hyp0 = all_hyps[list(all_hyps.keys())[0]]

        sercon.check_threshold(model, hyp0, 1000, 1000, 1000)

        threshold_cores = sercon.get_threshold_cores()
        sercon.set_threshold_cores(threshold_cores + 1)
        self.assertEqual(threshold_cores + 1, sercon.get_threshold_cores())

    def test_number_of(self):
        sercon = strategies.BasicConsolidation()
        sercon.get_number_of_released_nodes()
        sercon.get_number_of_migrations()

    def test_basic_consolidation_migration(self):
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        solution = sercon.execute(
            self.fake_cluster.generate_scenario_3_with_2_hypervisors())

        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        expected_num_migrations = 1
        expected_power_state = 0

        num_migrations = actions_counter.get("migrate", 0)
        num_hypervisor_state_change = actions_counter.get(
            "change_hypervisor_state", 0)
        self.assertEqual(expected_num_migrations, num_migrations)
        self.assertEqual(expected_power_state, num_hypervisor_state_change)

    # calculate_weight
    def test_execute_no_workload(self):
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        current_state_cluster = faker_cluster_state.FakerModelCollector()
        model = current_state_cluster. \
            generate_scenario_4_with_1_hypervisor_no_vm()

        with mock.patch.object(strategies.BasicConsolidation,
                               'calculate_weight') \
                as mock_score_call:
            mock_score_call.return_value = 0
            solution = sercon.execute(model)
            self.assertEqual(100, solution.efficacy)

    def test_check_parameters(self):
        sercon = strategies.BasicConsolidation()
        sercon.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        solution = sercon.execute(
            self.fake_cluster.generate_scenario_3_with_2_hypervisors())
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
