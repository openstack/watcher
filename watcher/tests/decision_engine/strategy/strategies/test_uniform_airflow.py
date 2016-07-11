# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel Corp
#
# Authors: Junjie-Huang <junjie.huang@intel.com>
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
from watcher.decision_engine.model import resource
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies \
    import faker_metrics_collector


class TestUniformAirflow(base.BaseTestCase):

    def setUp(self):
        super(TestUniformAirflow, self).setUp()
        # fake metrics
        self.fake_metrics = faker_metrics_collector.FakerMetricsCollector()
        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.UniformAirflow, "model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_ceilometer = mock.patch.object(
            strategies.UniformAirflow, "ceilometer",
            new_callable=mock.PropertyMock)
        self.m_ceilometer = p_ceilometer.start()
        self.addCleanup(p_ceilometer.stop)

        self.m_model.return_value = model_root.ModelRoot()
        self.m_ceilometer.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.strategy = strategies.UniformAirflow(config=mock.Mock())

    def test_calc_used_res(self):
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        hypervisor = model.get_hypervisor_from_id('Node_0')
        cap_cores = model.get_resource_from_id(resource.ResourceType.cpu_cores)
        cap_mem = model.get_resource_from_id(resource.ResourceType.memory)
        cap_disk = model.get_resource_from_id(resource.ResourceType.disk)
        cores_used, mem_used, disk_used = self.\
            strategy.calculate_used_resource(
                hypervisor, cap_cores, cap_mem, cap_disk)
        self.assertEqual((cores_used, mem_used, disk_used), (25, 4, 40))

    def test_group_hosts_by_airflow(self):
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        self.strategy.threshold_airflow = 300
        h1, h2 = self.strategy.group_hosts_by_airflow()
        # print h1, h2, avg, w_map
        self.assertEqual(h1[0]['hv'].uuid, 'Node_0')
        self.assertEqual(h2[0]['hv'].uuid, 'Node_1')

    def test_choose_vm_to_migrate(self):
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 22
        h1, h2 = self.strategy.group_hosts_by_airflow()
        vm_to_mig = self.strategy.choose_vm_to_migrate(h1)
        self.assertEqual(vm_to_mig[0].uuid, 'Node_0')
        self.assertEqual(len(vm_to_mig[1]), 1)
        self.assertEqual(vm_to_mig[1][0].uuid,
                         "cae81432-1631-4d4e-b29c-6f3acdcde906")

    def test_choose_vm_to_migrate_all(self):
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 25
        h1, h2 = self.strategy.group_hosts_by_airflow()
        vm_to_mig = self.strategy.choose_vm_to_migrate(h1)
        self.assertEqual(vm_to_mig[0].uuid, 'Node_0')
        self.assertEqual(len(vm_to_mig[1]), 2)
        self.assertEqual(vm_to_mig[1][1].uuid,
                         "73b09e16-35b7-4922-804e-e8f5d9b740fc")

    def test_choose_vm_notfound(self):
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 22
        h1, h2 = self.strategy.group_hosts_by_airflow()
        vms = model.get_all_vms()
        vms.clear()
        vm_to_mig = self.strategy.choose_vm_to_migrate(h1)
        self.assertEqual(vm_to_mig, None)

    def test_filter_destination_hosts(self):
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 22
        h1, h2 = self.strategy.group_hosts_by_airflow()
        vm_to_mig = self.strategy.choose_vm_to_migrate(h1)
        dest_hosts = self.strategy.filter_destination_hosts(h2, vm_to_mig[1])
        self.assertEqual(len(dest_hosts), 1)
        self.assertEqual(dest_hosts[0]['hv'].uuid, 'Node_1')
        self.assertEqual(dest_hosts[0]['vm'].uuid,
                         'cae81432-1631-4d4e-b29c-6f3acdcde906')

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
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 25
        self.strategy.threshold_power = 300
        model = self.fake_cluster.generate_scenario_4_with_1_hypervisor_no_vm()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        self.assertEqual([], solution.actions)

    def test_execute(self):
        self.strategy.threshold_airflow = 300
        self.strategy.threshold_inlet_t = 25
        self.strategy.threshold_power = 300
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        num_migrations = actions_counter.get("migrate", 0)
        self.assertEqual(num_migrations, 2)

    def test_check_parameters(self):
        model = self.fake_cluster.generate_scenario_7_with_2_hypervisors()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
