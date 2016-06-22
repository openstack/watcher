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

from watcher.applier.loading import default
from watcher.common import exception
from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies \
    import faker_metrics_collector


class TestBasicConsolidation(base.BaseTestCase):

    def setUp(self):
        super(TestBasicConsolidation, self).setUp()
        # fake metrics
        self.fake_metrics = faker_metrics_collector.FakerMetricsCollector()
        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.BasicConsolidation, "model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_ceilometer = mock.patch.object(
            strategies.BasicConsolidation, "ceilometer",
            new_callable=mock.PropertyMock)
        self.m_ceilometer = p_ceilometer.start()
        self.addCleanup(p_ceilometer.stop)

        self.m_model.return_value = model_root.ModelRoot()
        self.m_ceilometer.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.strategy = strategies.BasicConsolidation(config=mock.Mock())

    def test_cluster_size(self):
        size_cluster = len(
            self.fake_cluster.generate_scenario_1().get_all_hypervisors())
        size_cluster_assert = 5
        self.assertEqual(size_cluster_assert, size_cluster)

    def test_basic_consolidation_score_hypervisor(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_1_score = 0.023333333333333317
        self.assertEqual(node_1_score, self.strategy.calculate_score_node(
            model.get_hypervisor_from_id("Node_1")))
        node_2_score = 0.26666666666666666
        self.assertEqual(node_2_score, self.strategy.calculate_score_node(
            model.get_hypervisor_from_id("Node_2")))
        node_0_score = 0.023333333333333317
        self.assertEqual(node_0_score, self.strategy.calculate_score_node(
            model.get_hypervisor_from_id("Node_0")))

    def test_basic_consolidation_score_vm(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        vm_0 = model.get_vm_from_id("VM_0")
        vm_0_score = 0.023333333333333317
        self.assertEqual(vm_0_score, self.strategy.calculate_score_vm(vm_0))

        vm_1 = model.get_vm_from_id("VM_1")
        vm_1_score = 0.023333333333333317
        self.assertEqual(vm_1_score, self.strategy.calculate_score_vm(vm_1))
        vm_2 = model.get_vm_from_id("VM_2")
        vm_2_score = 0.033333333333333326
        self.assertEqual(vm_2_score, self.strategy.calculate_score_vm(vm_2))
        vm_6 = model.get_vm_from_id("VM_6")
        vm_6_score = 0.02666666666666669
        self.assertEqual(vm_6_score, self.strategy.calculate_score_vm(vm_6))
        vm_7 = model.get_vm_from_id("VM_7")
        vm_7_score = 0.013333333333333345
        self.assertEqual(vm_7_score, self.strategy.calculate_score_vm(vm_7))

    def test_basic_consolidation_score_vm_disk(self):
        model = self.fake_cluster.generate_scenario_5_with_vm_disk_0()
        self.m_model.return_value = model
        vm_0 = model.get_vm_from_id("VM_0")
        vm_0_score = 0.023333333333333355
        self.assertEqual(vm_0_score, self.strategy.calculate_score_vm(vm_0, ))

    def test_basic_consolidation_weight(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        vm_0 = model.get_vm_from_id("VM_0")
        cores = 16
        # 80 Go
        disk = 80
        # mem 8 Go
        mem = 8
        vm_0_weight_assert = 3.1999999999999997
        self.assertEqual(
            vm_0_weight_assert,
            self.strategy.calculate_weight(vm_0, cores, disk, mem))

    def test_calculate_migration_efficacy(self):
        self.strategy.calculate_migration_efficacy()

    def test_exception_model(self):
        self.m_model.return_value = None
        self.assertRaises(
            exception.ClusterStateNotDefined, self.strategy.execute)

    def test_exception_cluster_empty(self):
        model = model_root.ModelRoot()
        self.m_model.return_value = model
        self.assertRaises(exception.ClusterEmpty, self.strategy.execute)

    def test_check_migration(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model

        all_vms = model.get_all_vms()
        all_hyps = model.get_all_hypervisors()
        vm0 = all_vms[list(all_vms.keys())[0]]
        hyp0 = all_hyps[list(all_hyps.keys())[0]]

        self.strategy.check_migration(hyp0, hyp0, vm0)

    def test_threshold(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model

        all_hyps = model.get_all_hypervisors()
        hyp0 = all_hyps[list(all_hyps.keys())[0]]

        self.assertFalse(self.strategy.check_threshold(
            hyp0, 1000, 1000, 1000))

    def test_basic_consolidation_migration(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model

        solution = self.strategy.execute()

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
        model = (
            self.fake_cluster
            .generate_scenario_4_with_1_hypervisor_no_vm())
        self.m_model.return_value = model

        with mock.patch.object(
            strategies.BasicConsolidation, 'calculate_weight'
        ) as mock_score_call:
            mock_score_call.return_value = 0
            solution = self.strategy.execute()
            self.assertEqual(0, solution.efficacy.global_efficacy.value)

    def test_check_parameters(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
