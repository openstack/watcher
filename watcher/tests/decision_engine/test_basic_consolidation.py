# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
        node_1_score = 0.09862626262626262
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_1"),
                cluster), node_1_score)
        node_2_score = 0.29989898989898994
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_2"),
                cluster), node_2_score)
        node_0_score = 0.13967676767676765
        self.assertEqual(
            sercon.calculate_score_node(
                cluster.get_hypervisor_from_id("Node_0"),
                cluster), node_0_score)

    def test_basic_consolidation_score_vm(self):
        cluster = self.fake_cluster.generate_scenario_1()
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(self.fake_metrics)
        vm_0 = cluster.get_vm_from_id("VM_0")
        vm_0_score = 0.6
        self.assertEqual(sercon.calculate_score_vm(vm_0, cluster), vm_0_score)

        vm_1 = cluster.get_vm_from_id("VM_1")
        vm_1_score = 1.0999999999999999
        self.assertEqual(sercon.calculate_score_vm(vm_1, cluster),
                         vm_1_score)
        vm_2 = cluster.get_vm_from_id("VM_2")
        vm_2_score = 1.2
        self.assertEqual(sercon.calculate_score_vm(vm_2, cluster), vm_2_score)

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

    def test_basic_consolidation_efficiency(self):
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(self.fake_metrics)
        efficient_assert = 100
        solution = sercon.execute(self.fake_cluster.generate_scenario_1())
        self.assertEqual(solution.get_efficiency(), efficient_assert)

    def test_exception_model(self):
        sercon = BasicConsolidation()
        self.assertRaises(exception.ClusteStateNotDefined, sercon.execute,
                          None)

    def test_exception_cluster_empty(self):
        sercon = BasicConsolidation()
        model = ModelRoot()
        self.assertRaises(exception.ClusterEmpty, sercon.execute,
                          model)

    def test_exception_metric_collector(self):
        sercon = BasicConsolidation()
        self.assertRaises(exception.MetricCollectorNotDefined,
                          sercon.calculate_score_vm, "VM_1", None)

    def check_migration(self, array, indice, vm, src, dest):
        """Helper to check migration

        :param array:
        :param indice:
        :param vm:
        :param src:
        :param dest:
        :return:
        """
        self.assertEqual(array[indice].get_vm().get_uuid(), vm)
        self.assertEqual(array[indice].get_source_hypervisor().get_uuid(), src)
        self.assertEqual(array[indice].get_dest_hypervisor().get_uuid(), dest)

    def test_basic_consolidation_migration(self):
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(self.fake_metrics)

        solution = sercon.execute(self.fake_cluster.generate_scenario_1())

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

        self.assertEqual(change_hypervisor_state, 3)
        self.assertEqual(count_migration, 3)
        # check migration
        self.check_migration(migrate, 0, "VM_7", "Node_4", "Node_2")
        self.check_migration(migrate, 1, "VM_6", "Node_3", "Node_0")
        self.check_migration(migrate, 2, "VM_2", "Node_1", "Node_0")

    def test_basic_consolidation_random(self):
        metrics = FakerMetricsCollector()
        current_state_cluster = FakerStateCollector()

        sercon = BasicConsolidation("sercon", "Basic offline consolidation")
        sercon.set_metrics_resource_collector(metrics)

        solution = sercon.execute(
            current_state_cluster.generate_random(25, 2))

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
