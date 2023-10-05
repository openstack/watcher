# Copyright 2023 Cloudbase Solutions
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

try:
    from maas.client import enum as maas_enum
except ImportError:
    maas_enum = None

from watcher.common.metal_helper import constants as m_constants
from watcher.common.metal_helper import maas
from watcher.tests import base


class TestMaasNode(base.TestCase):
    def setUp(self):
        super().setUp()

        self._wrapped_node = mock.Mock()
        self._nova_node = mock.Mock()
        self._maas_client = mock.Mock()

        self._node = maas.MaasNode(
            self._wrapped_node, self._nova_node, self._maas_client)

    def test_get_power_state(self):
        if not maas_enum:
            self.skipTest("python-libmaas not intalled.")

        self._wrapped_node.query_power_state.side_effect = (
            maas_enum.PowerState.ON,
            maas_enum.PowerState.OFF,
            maas_enum.PowerState.ERROR,
            maas_enum.PowerState.UNKNOWN,
            'SomeOtherState')

        expected_states = (
            m_constants.PowerState.ON,
            m_constants.PowerState.OFF,
            m_constants.PowerState.ERROR,
            m_constants.PowerState.UNKNOWN,
            m_constants.PowerState.UNKNOWN)

        for expected_state in expected_states:
            actual_state = self._node.get_power_state()
            self.assertEqual(expected_state, actual_state)

    def test_get_id(self):
        self.assertEqual(
            self._wrapped_node.system_id,
            self._node.get_id())

    def test_power_on(self):
        self._node.power_on()
        self._wrapped_node.power_on.assert_called_once_with()

    def test_power_off(self):
        self._node.power_off()
        self._wrapped_node.power_off.assert_called_once_with()


class TestMaasHelper(base.TestCase):
    def setUp(self):
        super().setUp()

        self._mock_osc = mock.Mock()
        self._mock_nova_client = self._mock_osc.nova.return_value
        self._mock_maas_client = self._mock_osc.maas.return_value
        self._helper = maas.MaasHelper(osc=self._mock_osc)

    def test_list_compute_nodes(self):
        compute_fqdn = "compute-0"
        # some other MAAS node, not a Nova node
        ctrl_fqdn = "ctrl-1"

        mock_machines = [
            mock.Mock(fqdn=compute_fqdn,
                      system_id=mock.sentinel.compute_node_id),
            mock.Mock(fqdn=ctrl_fqdn,
                      system_id=mock.sentinel.ctrl_node_id),
        ]
        mock_hypervisors = [
            mock.Mock(hypervisor_hostname=compute_fqdn),
        ]

        self._mock_maas_client.machines.list.return_value = mock_machines
        self._mock_nova_client.hypervisors.list.return_value = mock_hypervisors

        out_nodes = self._helper.list_compute_nodes()
        self.assertEqual(1, len(out_nodes))

        out_node = out_nodes[0]
        self.assertIsInstance(out_node, maas.MaasNode)
        self.assertEqual(mock.sentinel.compute_node_id, out_node.get_id())
        self.assertEqual(compute_fqdn, out_node.get_hypervisor_hostname())

    def test_get_node(self):
        mock_machine = mock.Mock(fqdn='compute-0')
        self._mock_maas_client.machines.get.return_value = mock_machine

        mock_compute_nodes = [
            mock.Mock(hypervisor_hostname="compute-011"),
            mock.Mock(hypervisor_hostname="compute-0"),
            mock.Mock(hypervisor_hostname="compute-01"),
        ]
        self._mock_nova_client.hypervisors.search.return_value = (
            mock_compute_nodes)

        out_node = self._helper.get_node(mock.sentinel.id)

        self.assertEqual(mock_compute_nodes[1], out_node._nova_node)
        self.assertEqual(self._mock_maas_client, out_node._maas_client)
        self.assertEqual(mock_machine, out_node._maas_node)
