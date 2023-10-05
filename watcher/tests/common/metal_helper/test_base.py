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

from watcher.common import exception
from watcher.common.metal_helper import base as m_helper_base
from watcher.common.metal_helper import constants as m_constants
from watcher.tests import base


# The base classes have abstract methods, we'll need to
# stub them.
class MockMetalNode(m_helper_base.BaseMetalNode):
    def get_power_state(self):
        raise NotImplementedError()

    def get_id(self):
        raise NotImplementedError()

    def power_on(self):
        raise NotImplementedError()

    def power_off(self):
        raise NotImplementedError()


class MockMetalHelper(m_helper_base.BaseMetalHelper):
    def list_compute_nodes(self):
        pass

    def get_node(self, node_id):
        pass


class TestBaseMetalNode(base.TestCase):
    def setUp(self):
        super().setUp()

        self._nova_node = mock.Mock()
        self._node = MockMetalNode(self._nova_node)

    def test_get_hypervisor_node(self):
        self.assertEqual(
            self._nova_node,
            self._node.get_hypervisor_node())

    def test_get_hypervisor_node_missing(self):
        node = MockMetalNode()
        self.assertRaises(
            exception.Invalid,
            node.get_hypervisor_node)

    def test_get_hypervisor_hostname(self):
        self.assertEqual(
            self._nova_node.hypervisor_hostname,
            self._node.get_hypervisor_hostname())

    @mock.patch.object(MockMetalNode, 'power_on')
    @mock.patch.object(MockMetalNode, 'power_off')
    def test_set_power_state(self,
                             mock_power_off, mock_power_on):
        self._node.set_power_state(m_constants.PowerState.ON)
        mock_power_on.assert_called_once_with()

        self._node.set_power_state(m_constants.PowerState.OFF)
        mock_power_off.assert_called_once_with()

        self.assertRaises(
            exception.UnsupportedActionType,
            self._node.set_power_state,
            m_constants.PowerState.UNKNOWN)


class TestBaseMetalHelper(base.TestCase):
    def setUp(self):
        super().setUp()

        self._osc = mock.Mock()
        self._helper = MockMetalHelper(self._osc)

    def test_nova_client_attr(self):
        self.assertEqual(self._osc.nova.return_value,
                         self._helper.nova_client)
