# -*- encoding: utf-8 -*-
#
# Authors: Vojtech CIMA <cima@zhaw.ch>
#          Bruno GRAZIOLI <gaea@zhaw.ch>
#          Sean MURPHY <murp@zhaw.ch>
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
    import faker_cluster_and_metrics


class TestVMWorkloadConsolidation(base.BaseTestCase):

    def setUp(self):
        super(TestVMWorkloadConsolidation, self).setUp()

        # fake cluster
        self.fake_cluster = faker_cluster_and_metrics.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.VMWorkloadConsolidation, "model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_ceilometer = mock.patch.object(
            strategies.VMWorkloadConsolidation, "ceilometer",
            new_callable=mock.PropertyMock)
        self.m_ceilometer = p_ceilometer.start()
        self.addCleanup(p_ceilometer.stop)

        # fake metrics
        self.fake_metrics = faker_cluster_and_metrics.FakeCeilometerMetrics(
            self.m_model.return_value)

        self.m_model.return_value = model_root.ModelRoot()
        self.m_ceilometer.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.strategy = strategies.VMWorkloadConsolidation(config=mock.Mock())

    def test_get_vm_utilization(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        vm_0 = model.get_vm_from_id("VM_0")
        vm_util = dict(cpu=1.0, ram=1, disk=10)
        self.assertEqual(vm_util,
                         self.strategy.get_vm_utilization(vm_0.uuid, model))

    def test_get_hypervisor_utilization(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_hypervisor_from_id("Node_0")
        node_util = dict(cpu=1.0, ram=1, disk=10)
        self.assertEqual(
            node_util,
            self.strategy.get_hypervisor_utilization(node_0, model))

    def test_get_hypervisor_capacity(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        node_0 = model.get_hypervisor_from_id("Node_0")
        node_util = dict(cpu=40, ram=64, disk=250)
        self.assertEqual(node_util,
                         self.strategy.get_hypervisor_capacity(node_0, model))

    def test_get_relative_hypervisor_utilization(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        hypervisor = model.get_hypervisor_from_id('Node_0')
        rhu = self.strategy.get_relative_hypervisor_utilization(
            hypervisor, model)
        expected_rhu = {'disk': 0.04, 'ram': 0.015625, 'cpu': 0.025}
        self.assertEqual(expected_rhu, rhu)

    def test_get_relative_cluster_utilization(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        cru = self.strategy.get_relative_cluster_utilization(model)
        expected_cru = {'cpu': 0.05, 'disk': 0.05, 'ram': 0.0234375}
        self.assertEqual(expected_cru, cru)

    def test_add_migration(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h1 = model.get_hypervisor_from_id('Node_0')
        h2 = model.get_hypervisor_from_id('Node_1')
        vm_uuid = 'VM_0'
        self.strategy.add_migration(vm_uuid, h1, h2, model)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = {'action_type': 'migrate',
                    'input_parameters': {'dst_hypervisor': h2.uuid,
                                         'src_hypervisor': h1.uuid,
                                         'migration_type': 'live',
                                         'resource_id': vm_uuid}}
        self.assertEqual(expected, self.strategy.solution.actions[0])

    def test_is_overloaded(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h1 = model.get_hypervisor_from_id('Node_0')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.is_overloaded(h1, model, cc)
        self.assertEqual(False, res)

        cc = {'cpu': 0.025, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.is_overloaded(h1, model, cc)
        self.assertEqual(False, res)

        cc = {'cpu': 0.024, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.is_overloaded(h1, model, cc)
        self.assertEqual(True, res)

    def test_vm_fits(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h = model.get_hypervisor_from_id('Node_1')
        vm_uuid = 'VM_0'
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.vm_fits(vm_uuid, h, model, cc)
        self.assertEqual(True, res)

        cc = {'cpu': 0.025, 'ram': 1.0, 'disk': 1.0}
        res = self.strategy.vm_fits(vm_uuid, h, model, cc)
        self.assertEqual(False, res)

    def test_add_action_enable_hypervisor(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h = model.get_hypervisor_from_id('Node_0')
        self.strategy.add_action_enable_hypervisor(h)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {'state': 'enabled',
                                          'resource_id': 'Node_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_action_disable_hypervisor(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h = model.get_hypervisor_from_id('Node_0')
        self.strategy.add_action_disable_hypervisor(h)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {'state': 'disabled',
                                          'resource_id': 'Node_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_disable_unused_hypervisors(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h1 = model.get_hypervisor_from_id('Node_0')
        h2 = model.get_hypervisor_from_id('Node_1')
        vm_uuid = 'VM_0'
        self.strategy.disable_unused_hypervisors(model)
        self.assertEqual(0, len(self.strategy.solution.actions))

        # Migrate VM to free the hypervisor
        self.strategy.add_migration(vm_uuid, h1, h2, model)

        self.strategy.disable_unused_hypervisors(model)
        expected = {'action_type': 'change_nova_service_state',
                    'input_parameters': {'state': 'disabled',
                                         'resource_id': 'Node_0'}}
        self.assertEqual(2, len(self.strategy.solution.actions))
        self.assertEqual(expected, self.strategy.solution.actions[1])

    def test_offload_phase(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.offload_phase(model, cc)
        expected = []
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_consolidation_phase(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h1 = model.get_hypervisor_from_id('Node_0')
        h2 = model.get_hypervisor_from_id('Node_1')
        vm_uuid = 'VM_0'
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.consolidation_phase(model, cc)
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'dst_hypervisor': h2.uuid,
                                          'src_hypervisor': h1.uuid,
                                          'migration_type': 'live',
                                          'resource_id': vm_uuid}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_strategy(self):
        model = self.fake_cluster.generate_scenario_2()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h1 = model.get_hypervisor_from_id('Node_0')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.offload_phase(model, cc)
        self.strategy.consolidation_phase(model, cc)
        self.strategy.optimize_solution(model)
        h2 = self.strategy.solution.actions[0][
            'input_parameters']['dst_hypervisor']
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'dst_hypervisor': h2,
                                          'src_hypervisor': h1.uuid,
                                          'migration_type': 'live',
                                          'resource_id': 'VM_3'}},
                    {'action_type': 'migrate',
                     'input_parameters': {'dst_hypervisor': h2,
                                          'src_hypervisor': h1.uuid,
                                          'migration_type': 'live',
                                          'resource_id': 'VM_1'}}]

        self.assertEqual(expected, self.strategy.solution.actions)

    def test_strategy2(self):
        model = self.fake_cluster.generate_scenario_3()
        self.m_model.return_value = model
        self.fake_metrics.model = model
        h1 = model.get_hypervisor_from_id('Node_0')
        h2 = model.get_hypervisor_from_id('Node_1')
        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}
        self.strategy.offload_phase(model, cc)
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'dst_hypervisor': h2.uuid,
                                          'migration_type': 'live',
                                          'resource_id': 'VM_6',
                                          'src_hypervisor': h1.uuid}},
                    {'action_type': 'migrate',
                     'input_parameters': {'dst_hypervisor': h2.uuid,
                                          'migration_type': 'live',
                                          'resource_id': 'VM_7',
                                          'src_hypervisor': h1.uuid}},
                    {'action_type': 'migrate',
                     'input_parameters': {'dst_hypervisor': h2.uuid,
                                          'migration_type': 'live',
                                          'resource_id': 'VM_8',
                                          'src_hypervisor': h1.uuid}}]
        self.assertEqual(expected, self.strategy.solution.actions)
        self.strategy.consolidation_phase(model, cc)
        expected.append({'action_type': 'migrate',
                         'input_parameters': {'dst_hypervisor': h1.uuid,
                                              'migration_type': 'live',
                                              'resource_id': 'VM_7',
                                              'src_hypervisor': h2.uuid}})
        self.assertEqual(expected, self.strategy.solution.actions)
        self.strategy.optimize_solution(model)
        del expected[3]
        del expected[1]
        self.assertEqual(expected, self.strategy.solution.actions)
