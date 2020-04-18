# Copyright (c) 2017 ZTE
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import mock

import jsonschema

from watcher.applier.actions import base as baction
from watcher.applier.actions import change_node_power_state
from watcher.common import clients
from watcher.tests import base

COMPUTE_NODE = "compute-1"


@mock.patch.object(clients.OpenStackClients, 'nova')
@mock.patch.object(clients.OpenStackClients, 'ironic')
class TestChangeNodePowerState(base.TestCase):

    def setUp(self):
        super(TestChangeNodePowerState, self).setUp()

        self.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            "state": change_node_power_state.NodeState.POWERON.value,
        }
        self.action = change_node_power_state.ChangeNodePowerState(
            mock.Mock())
        self.action.input_parameters = self.input_parameters

    def test_parameters_down(self, mock_ironic, mock_nova):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            self.action.STATE:
                change_node_power_state.NodeState.POWEROFF.value}
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_up(self, mock_ironic, mock_nova):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            self.action.STATE:
                change_node_power_state.NodeState.POWERON.value}
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_exception_wrong_state(self, mock_ironic, mock_nova):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            self.action.STATE: 'error'}
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_resource_id_empty(self, mock_ironic, mock_nova):
        self.action.input_parameters = {
            self.action.STATE:
                change_node_power_state.NodeState.POWERON.value,
        }
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_applies_add_extra(self, mock_ironic, mock_nova):
        self.action.input_parameters = {"extra": "failed"}
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_change_service_state_pre_condition(self, mock_ironic, mock_nova):
        try:
            self.action.pre_condition()
        except Exception as exc:
            self.fail(exc)

    def test_change_node_state_post_condition(self, mock_ironic, mock_nova):
        try:
            self.action.post_condition()
        except Exception as exc:
            self.fail(exc)

    def test_execute_node_service_state_with_poweron_target(
            self, mock_ironic, mock_nova):
        mock_irclient = mock_ironic.return_value
        self.action.input_parameters["state"] = (
            change_node_power_state.NodeState.POWERON.value)
        mock_irclient.node.get.side_effect = [
            mock.MagicMock(power_state='power off'),
            mock.MagicMock(power_state='power on')]

        result = self.action.execute()
        self.assertTrue(result)

        mock_irclient.node.set_power_state.assert_called_once_with(
            COMPUTE_NODE, change_node_power_state.NodeState.POWERON.value)

    def test_execute_change_node_state_with_poweroff_target(
            self, mock_ironic, mock_nova):
        mock_irclient = mock_ironic.return_value
        mock_nvclient = mock_nova.return_value
        mock_get = mock.MagicMock()
        mock_get.to_dict.return_value = {'running_vms': 0}
        mock_nvclient.hypervisors.get.return_value = mock_get
        self.action.input_parameters["state"] = (
            change_node_power_state.NodeState.POWEROFF.value)
        mock_irclient.node.get.side_effect = [
            mock.MagicMock(power_state='power on'),
            mock.MagicMock(power_state='power on'),
            mock.MagicMock(power_state='power off')]
        result = self.action.execute()
        self.assertTrue(result)

        mock_irclient.node.set_power_state.assert_called_once_with(
            COMPUTE_NODE, change_node_power_state.NodeState.POWEROFF.value)

    def test_revert_change_node_state_with_poweron_target(
            self, mock_ironic, mock_nova):
        mock_irclient = mock_ironic.return_value
        mock_nvclient = mock_nova.return_value
        mock_get = mock.MagicMock()
        mock_get.to_dict.return_value = {'running_vms': 0}
        mock_nvclient.hypervisors.get.return_value = mock_get
        self.action.input_parameters["state"] = (
            change_node_power_state.NodeState.POWERON.value)
        mock_irclient.node.get.side_effect = [
            mock.MagicMock(power_state='power on'),
            mock.MagicMock(power_state='power on'),
            mock.MagicMock(power_state='power off')]
        self.action.revert()

        mock_irclient.node.set_power_state.assert_called_once_with(
            COMPUTE_NODE, change_node_power_state.NodeState.POWEROFF.value)

    def test_revert_change_node_state_with_poweroff_target(
            self, mock_ironic, mock_nova):
        mock_irclient = mock_ironic.return_value
        self.action.input_parameters["state"] = (
            change_node_power_state.NodeState.POWEROFF.value)
        mock_irclient.node.get.side_effect = [
            mock.MagicMock(power_state='power off'),
            mock.MagicMock(power_state='power on')]
        self.action.revert()

        mock_irclient.node.set_power_state.assert_called_once_with(
            COMPUTE_NODE, change_node_power_state.NodeState.POWERON.value)
