# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE
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

from watcher.common import clients
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_and_metrics


class TestSavingEnergy(base.TestCase):

    def setUp(self):
        super(TestSavingEnergy, self).setUp()

        mock_node1 = mock.Mock()
        mock_node2 = mock.Mock()
        mock_node1.to_dict.return_value = {
            'uuid': '922d4762-0bc5-4b30-9cb9-48ab644dd861'}
        mock_node2.to_dict.return_value = {
            'uuid': '922d4762-0bc5-4b30-9cb9-48ab644dd862'}
        self.fake_nodes = [mock_node1, mock_node2]

        # fake cluster
        self.fake_cluster = faker_cluster_and_metrics.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.SavingEnergy, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_ironic = mock.patch.object(
            clients.OpenStackClients, 'ironic')
        self.m_ironic = p_ironic.start()
        self.addCleanup(p_ironic.stop)

        p_nova = mock.patch.object(
            clients.OpenStackClients, 'nova')
        self.m_nova = p_nova.start()
        self.addCleanup(p_nova.stop)

        p_model = mock.patch.object(
            strategies.SavingEnergy, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_audit_scope = mock.patch.object(
            strategies.SavingEnergy, "audit_scope",
            new_callable=mock.PropertyMock
        )
        self.m_audit_scope = p_audit_scope.start()
        self.addCleanup(p_audit_scope.stop)

        self.m_audit_scope.return_value = mock.Mock()
        self.m_ironic.node.list.return_value = self.fake_nodes

        self.strategy = strategies.SavingEnergy(
            config=mock.Mock())
        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update(
            {'free_used_percent': 10.0,
             'min_free_hosts_num': 1})
        self.strategy.free_used_percent = 10.0
        self.strategy.min_free_hosts_num = 1
        self.strategy._ironic_client = self.m_ironic
        self.strategy._nova_client = self.m_nova

    def test_get_hosts_pool_with_vms_node_pool(self):
        mock_node1 = mock.Mock()
        mock_node2 = mock.Mock()
        mock_node1.to_dict.return_value = {
            'extra': {'compute_node_id': 1},
            'power_state': 'power on'}
        mock_node2.to_dict.return_value = {
            'extra': {'compute_node_id': 2},
            'power_state': 'power off'}
        self.m_ironic.node.get.side_effect = [mock_node1, mock_node2]

        mock_hyper1 = mock.Mock()
        mock_hyper2 = mock.Mock()
        mock_hyper1.to_dict.return_value = {
            'running_vms': 2, 'service': {'host': 'Node_0'}, 'state': 'up'}
        mock_hyper2.to_dict.return_value = {
            'running_vms': 2, 'service': {'host': 'Node_1'}, 'state': 'up'}
        self.m_nova.hypervisors.get.side_effect = [mock_hyper1, mock_hyper2]

        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 2)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 0)

    def test_get_hosts_pool_free_poweron_node_pool(self):
        mock_node1 = mock.Mock()
        mock_node2 = mock.Mock()
        mock_node1.to_dict.return_value = {
            'extra': {'compute_node_id': 1},
            'power_state': 'power on'}
        mock_node2.to_dict.return_value = {
            'extra': {'compute_node_id': 2},
            'power_state': 'power on'}
        self.m_ironic.node.get.side_effect = [mock_node1, mock_node2]

        mock_hyper1 = mock.Mock()
        mock_hyper2 = mock.Mock()
        mock_hyper1.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_0'}, 'state': 'up'}
        mock_hyper2.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_1'}, 'state': 'up'}
        self.m_nova.hypervisors.get.side_effect = [mock_hyper1, mock_hyper2]

        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 2)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 0)

    def test_get_hosts_pool_free_poweroff_node_pool(self):
        mock_node1 = mock.Mock()
        mock_node2 = mock.Mock()
        mock_node1.to_dict.return_value = {
            'extra': {'compute_node_id': 1},
            'power_state': 'power off'}
        mock_node2.to_dict.return_value = {
            'extra': {'compute_node_id': 2},
            'power_state': 'power off'}
        self.m_ironic.node.get.side_effect = [mock_node1, mock_node2]

        mock_hyper1 = mock.Mock()
        mock_hyper2 = mock.Mock()
        mock_hyper1.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_0'}, 'state': 'up'}
        mock_hyper2.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_1'}, 'state': 'up'}
        self.m_nova.hypervisors.get.side_effect = [mock_hyper1, mock_hyper2]

        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 2)

    def test_get_hosts_pool_with_node_out_model(self):
        mock_node1 = mock.Mock()
        mock_node2 = mock.Mock()
        mock_node1.to_dict.return_value = {
            'extra': {'compute_node_id': 1},
            'power_state': 'power off'}
        mock_node2.to_dict.return_value = {
            'extra': {'compute_node_id': 2},
            'power_state': 'power off'}
        self.m_ironic.node.get.side_effect = [mock_node1, mock_node2]

        mock_hyper1 = mock.Mock()
        mock_hyper2 = mock.Mock()
        mock_hyper1.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_0'}, 'state': 'up'}
        mock_hyper2.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_10'}, 'state': 'up'}
        self.m_nova.hypervisors.get.side_effect = [mock_hyper1, mock_hyper2]

        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 1)

    def test_save_energy_poweron(self):
        self.strategy.free_poweroff_node_pool = [
            '922d4762-0bc5-4b30-9cb9-48ab644dd861',
            '922d4762-0bc5-4b30-9cb9-48ab644dd862'
            ]
        self.strategy.save_energy()
        self.assertEqual(len(self.strategy.solution.actions), 1)
        action = self.strategy.solution.actions[0]
        self.assertEqual(action.get('input_parameters').get('state'), 'on')

    def test_save_energy_poweroff(self):
        self.strategy.free_poweron_node_pool = [
            '922d4762-0bc5-4b30-9cb9-48ab644dd861',
            '922d4762-0bc5-4b30-9cb9-48ab644dd862'
            ]
        self.strategy.save_energy()
        self.assertEqual(len(self.strategy.solution.actions), 1)
        action = self.strategy.solution.actions[0]
        self.assertEqual(action.get('input_parameters').get('state'), 'off')

    def test_execute(self):
        mock_node1 = mock.Mock()
        mock_node2 = mock.Mock()
        mock_node1.to_dict.return_value = {
            'extra': {'compute_node_id': 1},
            'power_state': 'power on'}
        mock_node2.to_dict.return_value = {
            'extra': {'compute_node_id': 2},
            'power_state': 'power on'}
        self.m_ironic.node.get.side_effect = [mock_node1, mock_node2]

        mock_hyper1 = mock.Mock()
        mock_hyper2 = mock.Mock()
        mock_hyper1.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_0'}, 'state': 'up'}
        mock_hyper2.to_dict.return_value = {
            'running_vms': 0, 'service': {'host': 'Node_1'}, 'state': 'up'}
        self.m_nova.hypervisors.get.side_effect = [mock_hyper1, mock_hyper2]

        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model

        solution = self.strategy.execute()
        self.assertEqual(len(solution.actions), 1)
