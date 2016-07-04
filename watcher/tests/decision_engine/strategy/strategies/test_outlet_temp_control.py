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

from watcher.applier.loading import default
from watcher.common import exception
from watcher.common import utils
from watcher.decision_engine.model import model_root
from watcher.decision_engine.model import resource
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies \
    import faker_metrics_collector


class TestOutletTempControl(base.BaseTestCase):

    def setUp(self):
        super(TestOutletTempControl, self).setUp()
        # fake metrics
        self.fake_metrics = faker_metrics_collector.FakerMetricsCollector()
        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.OutletTempControl, "model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_ceilometer = mock.patch.object(
            strategies.OutletTempControl, "ceilometer",
            new_callable=mock.PropertyMock)
        self.m_ceilometer = p_ceilometer.start()
        self.addCleanup(p_ceilometer.stop)

        self.m_model.return_value = model_root.ModelRoot()
        self.m_ceilometer.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.strategy = strategies.OutletTempControl(config=mock.Mock())

        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update({'threshold': 34.3})
        self.strategy.threshold = 34.3

    def test_calc_used_res(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model
        hypervisor = model.get_hypervisor_from_id('Node_0')
        cap_cores = model.get_resource_from_id(resource.ResourceType.cpu_cores)
        cap_mem = model.get_resource_from_id(resource.ResourceType.memory)
        cap_disk = model.get_resource_from_id(resource.ResourceType.disk)
        cores_used, mem_used, disk_used = self.strategy.calc_used_res(
            hypervisor, cap_cores, cap_mem, cap_disk)

        self.assertEqual((10, 2, 20), (cores_used, mem_used, disk_used))

    def test_group_hosts_by_outlet_temp(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model
        h1, h2 = self.strategy.group_hosts_by_outlet_temp()
        self.assertEqual('Node_1', h1[0]['hv'].uuid)
        self.assertEqual('Node_0', h2[0]['hv'].uuid)

    def test_choose_vm_to_migrate(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model
        h1, h2 = self.strategy.group_hosts_by_outlet_temp()
        vm_to_mig = self.strategy.choose_vm_to_migrate(h1)
        self.assertEqual('Node_1', vm_to_mig[0].uuid)
        self.assertEqual('a4cab39b-9828-413a-bf88-f76921bf1517',
                         vm_to_mig[1].uuid)

    def test_filter_dest_servers(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model
        h1, h2 = self.strategy.group_hosts_by_outlet_temp()
        vm_to_mig = self.strategy.choose_vm_to_migrate(h1)
        dest_hosts = self.strategy.filter_dest_servers(h2, vm_to_mig[1])
        self.assertEqual(1, len(dest_hosts))
        self.assertEqual('Node_0', dest_hosts[0]['hv'].uuid)

    def test_exception_model(self):
        self.m_model.return_value = None
        self.assertRaises(
            exception.ClusterStateNotDefined, self.strategy.execute)

    def test_exception_cluster_empty(self):
        model = model_root.ModelRoot()
        self.m_model.return_value = model
        self.assertRaises(exception.ClusterEmpty, self.strategy.execute)

    def test_execute_cluster_empty(self):
        model = model_root.ModelRoot()
        self.m_model.return_value = model
        self.assertRaises(exception.ClusterEmpty, self.strategy.execute)

    def test_execute_no_workload(self):
        model = self.fake_cluster.generate_scenario_4_with_1_hypervisor_no_vm()
        self.m_model.return_value = model

        solution = self.strategy.execute()
        self.assertEqual([], solution.actions)

    def test_execute(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        num_migrations = actions_counter.get("migrate", 0)
        self.assertEqual(1, num_migrations)

    def test_check_parameters(self):
        model = self.fake_cluster.generate_scenario_3_with_2_hypervisors()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
