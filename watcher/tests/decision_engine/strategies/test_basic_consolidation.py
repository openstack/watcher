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
import mock
from watcher.common import exception

from watcher.decision_engine.framework.meta_actions.hypervisor_state import \
    ChangeHypervisorState
from watcher.decision_engine.framework.meta_actions.power_state import \
    ChangePowerState

from watcher.decision_engine.framework.meta_actions.migrate import Migrate
from watcher.decision_engine.framework.model.model_root import ModelRoot
from watcher.decision_engine.strategies.basic_consolidation import \
    BasicConsolidation
from watcher.tests import base
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector
from watcher.tests.decision_engine.faker_metrics_collector import \
    FakerMetricsCollector
# from watcher.tests.decision_engine.faker_metrics_collector import \
#    FakerMetricsCollectorEmptyType


class TestBasicConsolidation(base.BaseTestCase):
    # fake metrics
    fake_metrics = FakerMetricsCollector()

    # fake cluster
    fake_cluster = FakerStateCollector()

    def test_cluster_size(self):
        size_cluster = len(
            self.fake_cluster.generate_scenario_1().get_all_hypervisors())
        size_cluster_assert = 5
        self.assertEqual(size_cluster, size_cluster_assert)

    def test_basic_consolidation_score_hypervisor(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(self.fake_metrics)
        node_1_score = 0.01666666666666668
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_1"),
                cluster), node_1_score)
        node_2_score = 0.01666666666666668
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_2"),
                cluster), node_2_score)
        node_0_score = 0.01666666666666668
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_0"),
                cluster), node_0_score)

    def test_basic_consolidation_score_vm(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(self.fake_metrics)
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

    def test_basic_consolidation_weight(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(self.fake_metrics)
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

    def test_calculate_score_vm_raise_metric_collector(self):
        sercon = BasicConsolidation()
        self.assertRaises(exception.MetricCollectorNotDefined,
                          sercon.calculate_score_vm, "VM_1", None)

    def test_calculate_score_vm_raise_cluster_state_not_found(self):
        metrics = FakerMetricsCollector()
        metrics.empty_one_metric("CPU_COMPUTE")
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(metrics)
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
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()

        all_vms = model.get_all_vms()
        all_hyps = model.get_all_hypervisors()
        vm0 = all_vms[all_vms.keys()[0]]
        hyp0 = all_hyps[all_hyps.keys()[0]]

        sercon.check_migration(model, hyp0, hyp0, vm0)

    def test_threshold(self):
        sercon = BasicConsolidation()
        fake_cluster = FakerStateCollector()
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

    def test_calculate_score_node_raise_1(self):
        sercon = BasicConsolidation()
        metrics = FakerStateCollector()

        model = metrics.generate_scenario_4_with_2_hypervisors()
        all_hyps = model.get_all_hypervisors()
        hyp0 = all_hyps[all_hyps.keys()[0]]

        self.assertRaises(exception.MetricCollectorNotDefined,
                          sercon.calculate_score_node, hyp0, model)

    def test_calculate_score_node_raise_cpu_compute(self):
        metrics = FakerMetricsCollector()
        metrics.empty_one_metric("CPU_COMPUTE")
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(metrics)
        current_state_cluster = FakerStateCollector()
        model = current_state_cluster.generate_scenario_4_with_2_hypervisors()

        all_hyps = model.get_all_hypervisors()
        hyp0 = all_hyps[all_hyps.keys()[0]]

        self.assertRaises(exception.NoDataFound,
                          sercon.calculate_score_node, hyp0, model)

    """
    def test_calculate_score_node_raise_memory_compute(self):
        metrics = FakerMetricsCollector()
        metrics.empty_one_metric("MEM_COMPUTE")
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(metrics)
        current_state_cluster = FakerStateCollector()
        model = current_state_cluster.generate_scenario_4_with_2_hypervisors()

        all_hyps = model.get_all_hypervisors()
        hyp0 = all_hyps[all_hyps.keys()[0]]
        self.assertRaises(exception.NoDataFound,
                          sercon.calculate_score_node, hyp0, model)

    def test_calculate_score_node_raise_disk_compute(self):
        metrics = FakerMetricsCollector()
        metrics.empty_one_metric("DISK_COMPUTE")
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(metrics)
        current_state_cluster = FakerStateCollector()
        model = current_state_cluster.generate_scenario_4_with_2_hypervisors()

        all_hyps = model.get_all_hypervisors()
        hyp0 = all_hyps[all_hyps.keys()[0]]

        self.assertRaises(exception.NoDataFound,
                          sercon.calculate_score_node, hyp0, model)
    """

    def test_basic_consolidation_migration(self):
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(FakerMetricsCollector())
        solution = None
        solution = sercon.execute(FakerStateCollector().generate_scenario_1())

        count_migration = 0
        change_hypervisor_state = 0
        change_power_state = 0
        migrate = []
        for action in solution.meta_actions:
            if isinstance(action, Migrate):
                count_migration += 1
                migrate.append(action)
            if isinstance(action, ChangeHypervisorState):
                change_hypervisor_state += 1
            if isinstance(action, ChangePowerState):
                change_power_state += 1

        # self.assertEqual(change_hypervisor_state, 1)
        # self.assertEqual(count_migration, 2)

    def test_execute_cluster_empty(self):
        metrics = FakerMetricsCollector()
        current_state_cluster = FakerStateCollector()

        sercon = BasicConsolidation("sercon", "Basic offline consolidation")
        sercon.set_metrics_resource_collector(metrics)
        model = current_state_cluster.generate_random(0, 0)
        self.assertRaises(exception.ClusterEmpty, sercon.execute, model)

    def test_basic_consolidation_random(self):
        metrics = FakerMetricsCollector()
        current_state_cluster = FakerStateCollector()

        sercon = BasicConsolidation("sercon", "Basic offline consolidation")
        sercon.set_metrics_resource_collector(metrics)

        solution = sercon.execute(
            current_state_cluster.generate_random(25, 2))
        solution.__str__()

        count_migration = 0
        change_hypervisor_state = 0
        change_power_state = 0
        migrate = []
        for action in solution.meta_actions:
            if isinstance(action, Migrate):
                count_migration += 1
                migrate.append(action)
            if isinstance(action, ChangeHypervisorState):
                change_hypervisor_state += 1
            if isinstance(action, ChangePowerState):
                change_power_state += 1

    # calculate_weight
    def test_execute_no_workload(self):
        metrics = FakerMetricsCollector()
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(metrics)
        current_state_cluster = FakerStateCollector()
        model = current_state_cluster.\
            generate_scenario_5_with_1_hypervisor_no_vm()

        with mock.patch.object(BasicConsolidation, 'calculate_weight') \
                as mock_score_call:
            mock_score_call.return_value = 0
            solution = sercon.execute(model)
            self.assertEqual(solution.efficiency, 100)
