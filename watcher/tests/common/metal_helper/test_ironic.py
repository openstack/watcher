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

from watcher.common.metal_helper import constants as m_constants
from watcher.common.metal_helper import ironic
from watcher.tests import base


class TestIronicNode(base.TestCase):
    def setUp(self):
        super().setUp()

        self._wrapped_node = mock.Mock()
        self._nova_node = mock.Mock()
        self._ironic_client = mock.Mock()

        self._node = ironic.IronicNode(
            self._wrapped_node, self._nova_node, self._ironic_client)

    def test_get_power_state(self):
        states = (
            "power on",
            "power off",
            "rebooting",
            "soft power off",
            "soft reboot",
            'SomeOtherState')
        type(self._wrapped_node).power_state = mock.PropertyMock(
            side_effect=states)

        expected_states = (
            m_constants.PowerState.ON,
            m_constants.PowerState.OFF,
            m_constants.PowerState.ON,
            m_constants.PowerState.OFF,
            m_constants.PowerState.ON,
            m_constants.PowerState.UNKNOWN)

        for expected_state in expected_states:
            actual_state = self._node.get_power_state()
            self.assertEqual(expected_state, actual_state)

    def test_get_id(self):
        self.assertEqual(
            self._wrapped_node.uuid,
            self._node.get_id())

    def test_power_on(self):
        self._node.power_on()
        self._ironic_client.node.set_power_state.assert_called_once_with(
            self._wrapped_node.uuid, "on")

    def test_power_off(self):
        self._node.power_off()
        self._ironic_client.node.set_power_state.assert_called_once_with(
            self._wrapped_node.uuid, "off")


class TestIronicHelper(base.TestCase):
    def setUp(self):
        super().setUp()

        self._mock_osc = mock.Mock()
        self._mock_nova_client = self._mock_osc.nova.return_value
        self._mock_ironic_client = self._mock_osc.ironic.return_value
        self._helper = ironic.IronicHelper(osc=self._mock_osc)

    def test_list_compute_nodes(self):
        mock_machines = [
            mock.Mock(
                extra=dict(compute_node_id=mock.sentinel.compute_node_id)),
            mock.Mock(
                extra=dict(compute_node_id=mock.sentinel.compute_node_id2)),
            mock.Mock(
                extra=dict())
        ]
        mock_hypervisor = mock.Mock()

        self._mock_ironic_client.node.list.return_value = mock_machines
        self._mock_ironic_client.node.get.side_effect = mock_machines
        self._mock_nova_client.hypervisors.get.side_effect = (
            mock_hypervisor, None)

        out_nodes = self._helper.list_compute_nodes()
        self.assertEqual(1, len(out_nodes))

        out_node = out_nodes[0]
        self.assertIsInstance(out_node, ironic.IronicNode)
        self.assertEqual(mock_hypervisor, out_node._nova_node)
        self.assertEqual(mock_machines[0], out_node._ironic_node)
        self.assertEqual(self._mock_ironic_client, out_node._ironic_client)

    def test_get_node(self):
        mock_machine = mock.Mock(
            extra=dict(compute_node_id=mock.sentinel.compute_node_id))
        self._mock_ironic_client.node.get.return_value = mock_machine

        out_node = self._helper.get_node(mock.sentinel.id)

        self.assertEqual(self._mock_nova_client.hypervisors.get.return_value,
                         out_node._nova_node)
        self.assertEqual(self._mock_ironic_client, out_node._ironic_client)
        self.assertEqual(mock_machine, out_node._ironic_node)

    def test_get_node_not_a_hypervisor(self):
        mock_machine = mock.Mock(extra=dict(compute_node_id=None))
        self._mock_ironic_client.node.get.return_value = mock_machine

        out_node = self._helper.get_node(mock.sentinel.id)

        self._mock_nova_client.hypervisors.get.assert_not_called()
        self.assertIsNone(out_node._nova_node)
        self.assertEqual(self._mock_ironic_client, out_node._ironic_client)
        self.assertEqual(mock_machine, out_node._ironic_node)
