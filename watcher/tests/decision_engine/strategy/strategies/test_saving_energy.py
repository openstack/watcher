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

from unittest import mock

from watcher.common import clients
from watcher.common.metal_helper import constants as m_constants
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine import fake_metal_helper
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestSavingEnergy(TestBaseStrategy):

    def setUp(self):
        super(TestSavingEnergy, self).setUp()

        self.fake_nodes = [fake_metal_helper.get_mock_metal_node(),
                           fake_metal_helper.get_mock_metal_node()]
        self._metal_helper = mock.Mock()
        self._metal_helper.list_compute_nodes.return_value = self.fake_nodes

        p_nova = mock.patch.object(clients.OpenStackClients, 'nova')
        self.m_nova = p_nova.start()
        self.addCleanup(p_nova.stop)

        self.m_c_model.return_value = self.fake_c_cluster.generate_scenario_1()

        self.strategy = strategies.SavingEnergy(
            config=mock.Mock())
        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update(
            {'free_used_percent': 10.0,
             'min_free_hosts_num': 1})
        self.strategy.free_used_percent = 10.0
        self.strategy.min_free_hosts_num = 1
        self.strategy._metal_helper = self._metal_helper
        self.strategy._nova_client = self.m_nova

    def test_get_hosts_pool_with_vms_node_pool(self):
        self._metal_helper.list_compute_nodes.return_value = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON,
                hostname='hostname_0',
                running_vms=2),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF,
                hostname='hostname_1',
                running_vms=2),
        ]

        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 2)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 0)

    def test_get_hosts_pool_free_poweron_node_pool(self):
        self._metal_helper.list_compute_nodes.return_value = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON,
                hostname='hostname_0',
                running_vms=0),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON,
                hostname='hostname_1',
                running_vms=0),
        ]

        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 2)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 0)

    def test_get_hosts_pool_free_poweroff_node_pool(self):
        self._metal_helper.list_compute_nodes.return_value = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF,
                hostname='hostname_0',
                running_vms=0),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF,
                hostname='hostname_1',
                running_vms=0),
        ]

        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 2)

    def test_get_hosts_pool_with_node_out_model(self):
        self._metal_helper.list_compute_nodes.return_value = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF,
                hostname='hostname_0',
                running_vms=0),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF,
                hostname='hostname_10',
                running_vms=0),
        ]
        self.strategy.get_hosts_pool()

        self.assertEqual(len(self.strategy.with_vms_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweron_node_pool), 0)
        self.assertEqual(len(self.strategy.free_poweroff_node_pool), 1)

    def test_save_energy_poweron(self):
        self.strategy.free_poweroff_node_pool = [
            fake_metal_helper.get_mock_metal_node(),
            fake_metal_helper.get_mock_metal_node(),
        ]
        self.strategy.save_energy()
        self.assertEqual(len(self.strategy.solution.actions), 1)
        action = self.strategy.solution.actions[0]
        self.assertEqual(action.get('input_parameters').get('state'), 'on')

    def test_save_energy_poweroff(self):
        self.strategy.free_poweron_node_pool = [
            mock.Mock(uuid='922d4762-0bc5-4b30-9cb9-48ab644dd861'),
            mock.Mock(uuid='922d4762-0bc5-4b30-9cb9-48ab644dd862')
            ]
        self.strategy.save_energy()
        self.assertEqual(len(self.strategy.solution.actions), 1)
        action = self.strategy.solution.actions[0]
        self.assertEqual(action.get('input_parameters').get('state'), 'off')

    def test_execute(self):
        self._metal_helper.list_compute_nodes.return_value = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON,
                hostname='hostname_0',
                running_vms=0),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON,
                hostname='hostname_1',
                running_vms=0),
        ]

        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model

        solution = self.strategy.execute()
        self.assertEqual(len(solution.actions), 1)
