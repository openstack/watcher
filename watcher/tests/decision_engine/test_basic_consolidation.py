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
from collections import Counter

import mock
from mock import MagicMock

from watcher.common import exception

from watcher.decision_engine.meta_action.hypervisor_state import \
    ChangeHypervisorState
from watcher.decision_engine.meta_action.power_state import ChangePowerState

from watcher.decision_engine.meta_action.migrate import Migrate
from watcher.decision_engine.model.model_root import ModelRoot
from watcher.decision_engine.strategy.basic_consolidation import \
    BasicConsolidation
from watcher.tests import base
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerModelCollector
from watcher.tests.decision_engine.faker_metrics_collector import \
    FakerMetricsCollector


class TestBasicConsolidation(base.BaseTestCase):
    # fake metrics
    fake_metrics = FakerMetricsCollector()

    # fake cluster
    fake_cluster = FakerModelCollector()

    def test_cluster_size(self):
        size_cluster = len(
            self.fake_cluster.generate_scenario_1().get_all_hypervisors())
        size_cluster_assert = 5
        self.assertEqual(size_cluster, size_cluster_assert)

    def test_basic_consolidation_score_hypervisor(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = BasicConsolidation()
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        node_1_score = 0.023333333333333317
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_1"),
                cluster), node_1_score)
        node_2_score = 0.26666666666666666
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_2"),
                cluster), node_2_score)
        node_0_score = 0.023333333333333317
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_0"),
                cluster), node_0_score)

    def test_basic_consolidation_score_vm(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = BasicConsolidation()
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        vm_0 = cluster.get_vm_from_id("VM_0")
        vm_0_score = 0.0
        self.assertEqual(sercon.calculate_score_vm(vm_0, cluster), vm_0_score)

        vm_1 = cluster.get_vm_from_id("VM_1")
        vm_1_score = 0.0
        self.assertEqual(sercon.calculate_score_vm(vm_1, cluster),
                         vm_1_score)
        vm_2 = cluster.get_vm_from_id("VM_2")
        vm_2_score = 0.0
        self.assertEqual(sercon.calculate_score_vm(vm_2, cluster), vm_2_score)
        vm_6 = cluster.get_vm_from_id("VM_6")
        vm_6_score = 0.0
        self.assertEqual(sercon.calculate_score_vm(vm_6, cluster), vm_6_score)
        vm_7 = cluster.get_vm_from_id("VM_7")
        vm_7_score = 0.0
        self.assertEqual(sercon.calculate_score_vm(vm_7, cluster), vm_7_score)

    def test_basic_consolidation_score_vm_disk(self):
        cluster = self.fake_cluster.generate_scenario_5_with_vm_disk_0()
        sercon = BasicConsolidation()
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        vm_0 = cluster.get_vm_from_id("VM_0")
        vm_0_score = 0.0
        self.assertEqual(sercon.calculate_score_vm(vm_0, cluster), vm_0_score)

    def test_basic_consolidation_weight(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = BasicConsolidation()
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        vm_0 = cluster.get_vm_from_id("VM_0")
        cores = 16
        # 80 Go
        disk = 80
        # mem 8 Go
        mem = 8
        vm_0_weight_assert = 3.1999999999999997
        self.assertEqual(sercon.calculate_weight(cluster, vm_0, cores, disk,
                                                 mem),
                         vm_0_weight_assert)

    def test_calculate_migration_efficiency(self):
        sercon = BasicConsolidation()
        sercon.calculate_migration_efficiency()

    def test_exception_model(self):
        sercon = BasicConsolidation()
        self.assertRaises(exception.ClusteStateNotDefined, sercon.execute,
                          None)

    def test_exception_cluster_empty(self):
        sercon = BasicConsolidation()
        model = ModelRoot()
        self.assertRaises(exception.ClusterEmpty, sercon.execute,
                          model)

    def test_calculate_score_vm_raise_cluster_state_not_found(self):
        metrics = FakerMetricsCollector()
        metrics.empty_one_metric("CPU_COMPUTE")
        sercon = BasicConsolidation()
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        self.assertRaises(exception.ClusteStateNotDefined,
                          sercon.calculate_score_vm, "VM_1", None)

    def test_print_utilization_raise_cluster_state_not_found(self):
        sercon = BasicConsolidation()
        self.assertRaises(exception.ClusteStateNotDefined,
                          sercon.print_utilization, None)

    def check_migration(self, array, indice, vm, src, dest):
        """Helper to check migration

        :param array:
        :param indice:
        :param vm:
        :param src:
        :param dest:
        :return:
        """
        self.assertEqual(array[indice].get_vm().uuid, vm)
        self.assertEqual(array[indice].get_source_hypervisor().uuid, src)
        self.assertEqual(array[indice].get_dest_hypervisor().uuid, dest)

        self.assertEqual(array[indice].get_bandwidth(), 0)
        array[indice].set_bandwidth(5)
        self.assertEqual(array[indice].get_bandwidth(), 5)

    def test_check_migration(self):
        sercon = BasicConsolidation()
        fake_cluster = FakerModelCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()

        all_vms = model.get_all_vms()
        all_hyps = model.get_all_hypervisors()
        vm0 = all_vms[all_vms.keys()[0]]
        hyp0 = all_hyps[all_hyps.keys()[0]]

        sercon.check_migration(model, hyp0, hyp0, vm0)

    def test_threshold(self):
        sercon = BasicConsolidation()
        fake_cluster = FakerModelCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()

        all_hyps = model.get_all_hypervisors()
        hyp0 = all_hyps[all_hyps.keys()[0]]

        sercon.check_threshold(model, hyp0, 1000, 1000, 1000)

        threshold_cores = sercon.get_threshold_cores()
        sercon.set_threshold_cores(threshold_cores + 1)
        self.assertEqual(sercon.get_threshold_cores(), threshold_cores + 1)

    def test_number_of(self):
        sercon = BasicConsolidation()
        sercon.get_number_of_released_nodes()
        sercon.get_number_of_migrations()

    def test_basic_consolidation_migration(self):
        sercon = BasicConsolidation()
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        solution = sercon.execute(
            self.fake_cluster.generate_scenario_3())

        actions_counter = Counter(
            [type(action) for action in solution.meta_actions])

        expected_num_migrations = 0
        expected_power_state = 0
        expected_change_hypervisor_state = 0

        num_migrations = actions_counter.get(Migrate, 0)
        num_hypervisor_state_change = actions_counter.get(
            ChangeHypervisorState, 0)
        num_power_state_change = actions_counter.get(
            ChangePowerState, 0)

        self.assertEqual(num_migrations, expected_num_migrations)
        self.assertEqual(num_hypervisor_state_change, expected_power_state)
        self.assertEqual(num_power_state_change,
                         expected_change_hypervisor_state)

    def test_execute_cluster_empty(self):
        current_state_cluster = FakerModelCollector()
        sercon = BasicConsolidation("sercon", "Basic offline consolidation")
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        model = current_state_cluster.generate_random(0, 0)
        self.assertRaises(exception.ClusterEmpty, sercon.execute, model)

    # calculate_weight
    def test_execute_no_workload(self):
        sercon = BasicConsolidation()
        sercon.ceilometer = MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        current_state_cluster = FakerModelCollector()
        model = current_state_cluster. \
            generate_scenario_5_with_1_hypervisor_no_vm()

        with mock.patch.object(BasicConsolidation, 'calculate_weight') \
                as mock_score_call:
            mock_score_call.return_value = 0
            solution = sercon.execute(model)
            self.assertEqual(solution.efficiency, 100)
