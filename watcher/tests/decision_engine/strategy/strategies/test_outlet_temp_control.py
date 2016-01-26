# -*- encoding: utf-8 -*-
# Copyright (c) 2015 Intel Corp
#
# Authors: Zhenzan Zhou <zhenzan.zhou@intel.com>
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
from watcher.decision_engine.model import resource
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies \
    import faker_metrics_collector


class TestOutletTempControl(base.BaseTestCase):
    # fake metrics
    fake_metrics = faker_metrics_collector.FakerMetricsCollector()

    # fake cluster
    fake_cluster = faker_cluster_state.FakerModelCollector()

    def test_calc_used_res(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        strategy = strategies.OutletTempControl()
        hypervisor = model.get_hypervisor_from_id('Node_0')
        cap_cores = model.get_resource_from_id(resource.ResourceType.cpu_cores)
        cap_mem = model.get_resource_from_id(resource.ResourceType.memory)
        cap_disk = model.get_resource_from_id(resource.ResourceType.disk)
        cores_used, mem_used, disk_used = strategy.calc_used_res(model,
                                                                 hypervisor,
                                                                 cap_cores,
                                                                 cap_mem,
                                                                 cap_disk)

        self.assertEqual((cores_used, mem_used, disk_used), (10, 2, 20))

    def test_group_hosts_by_outlet_temp(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        strategy = strategies.OutletTempControl()
        strategy.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        h1, h2 = strategy.group_hosts_by_outlet_temp(model)
        self.assertEqual(h1[0]['hv'].uuid, 'Node_1')
        self.assertEqual(h2[0]['hv'].uuid, 'Node_0')

    def test_choose_vm_to_migrate(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        strategy = strategies.OutletTempControl()
        strategy.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        h1, h2 = strategy.group_hosts_by_outlet_temp(model)
        vm_to_mig = strategy.choose_vm_to_migrate(model, h1)
        self.assertEqual(vm_to_mig[0].uuid, 'Node_1')
        self.assertEqual(vm_to_mig[1].uuid,
                         "a4cab39b-9828-413a-bf88-f76921bf1517")

    def test_filter_dest_servers(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        strategy = strategies.OutletTempControl()
        strategy.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        h1, h2 = strategy.group_hosts_by_outlet_temp(model)
        vm_to_mig = strategy.choose_vm_to_migrate(model, h1)
        dest_hosts = strategy.filter_dest_servers(model, h2, vm_to_mig[1])
        self.assertEqual(len(dest_hosts), 1)
        self.assertEqual(dest_hosts[0]['hv'].uuid, 'Node_0')

    def test_exception_model(self):
        strategy = strategies.OutletTempControl()
        self.assertRaises(exception.ClusterStateNotDefined, strategy.execute,
                          None)

    def test_exception_cluster_empty(self):
        strategy = strategies.OutletTempControl()
        model = model_root.ModelRoot()
        self.assertRaises(exception.ClusterEmpty, strategy.execute, model)

    def test_execute_cluster_empty(self):
        strategy = strategies.OutletTempControl()
        strategy.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        model = model_root.ModelRoot()
        self.assertRaises(exception.ClusterEmpty, strategy.execute, model)

    def test_execute_no_workload(self):
        strategy = strategies.OutletTempControl()
        strategy.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)

        current_state_cluster = faker_cluster_state.FakerModelCollector()
        model = current_state_cluster. \
            generate_scenario_4_with_1_hypervisor_no_vm()

        solution = strategy.execute(model)
        self.assertEqual(solution.actions, [])

    def test_execute(self):
        strategy = strategies.OutletTempControl()
        strategy.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        solution = strategy.execute(model)
        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        num_migrations = actions_counter.get("migrate", 0)
        self.assertEqual(num_migrations, 1)

    def test_check_parameters(self):
        outlet = strategies.OutletTempControl()
        outlet.ceilometer = mock.MagicMock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        solution = outlet.execute(model)
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
