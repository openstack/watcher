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
from watcher.common.metal_helper import constants as m_constants
from watcher.common.metal_helper import factory as m_helper_factory
from watcher.tests import base
from watcher.tests.decision_engine import fake_metal_helper

COMPUTE_NODE = "compute-1"


class TestChangeNodePowerState(base.TestCase):

    def setUp(self):
        super(TestChangeNodePowerState, self).setUp()

        p_m_factory = mock.patch.object(m_helper_factory, 'get_helper')
        m_factory = p_m_factory.start()
        self._metal_helper = m_factory.return_value
        self.addCleanup(p_m_factory.stop)

        # Let's avoid unnecessary sleep calls while running the test.
        p_sleep = mock.patch('time.sleep')
        p_sleep.start()
        self.addCleanup(p_sleep.stop)

        self.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            "state": m_constants.PowerState.ON.value,
        }
        self.action = change_node_power_state.ChangeNodePowerState(
            mock.Mock())
        self.action.input_parameters = self.input_parameters

    def test_parameters_down(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            self.action.STATE:
                m_constants.PowerState.OFF.value}
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_up(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            self.action.STATE:
                m_constants.PowerState.ON.value}
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_exception_wrong_state(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: COMPUTE_NODE,
            self.action.STATE: 'error'}
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_resource_id_empty(self):
        self.action.input_parameters = {
            self.action.STATE:
                m_constants.PowerState.ON.value,
        }
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_applies_add_extra(self):
        self.action.input_parameters = {"extra": "failed"}
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_change_service_state_pre_condition(self):
        try:
            self.action.pre_condition()
        except Exception as exc:
            self.fail(exc)

    def test_change_node_state_post_condition(self):
        try:
            self.action.post_condition()
        except Exception as exc:
            self.fail(exc)

    def test_execute_node_service_state_with_poweron_target(self):
        self.action.input_parameters["state"] = (
            m_constants.PowerState.ON.value)
        mock_nodes = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON)
        ]
        self._metal_helper.get_node.side_effect = mock_nodes

        result = self.action.execute()
        self.assertTrue(result)

        mock_nodes[0].set_power_state.assert_called_once_with(
            m_constants.PowerState.ON.value)

    def test_execute_change_node_state_with_poweroff_target(self):
        self.action.input_parameters["state"] = (
            m_constants.PowerState.OFF.value)

        mock_nodes = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF)
        ]
        self._metal_helper.get_node.side_effect = mock_nodes

        result = self.action.execute()
        self.assertTrue(result)

        mock_nodes[0].set_power_state.assert_called_once_with(
            m_constants.PowerState.OFF.value)

    def test_revert_change_node_state_with_poweron_target(self):
        self.action.input_parameters["state"] = (
            m_constants.PowerState.ON.value)

        mock_nodes = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF)
        ]
        self._metal_helper.get_node.side_effect = mock_nodes

        self.action.revert()

        mock_nodes[0].set_power_state.assert_called_once_with(
            m_constants.PowerState.OFF.value)

    def test_revert_change_node_state_with_poweroff_target(self):
        self.action.input_parameters["state"] = (
            m_constants.PowerState.OFF.value)
        mock_nodes = [
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.OFF),
            fake_metal_helper.get_mock_metal_node(
                power_state=m_constants.PowerState.ON)
        ]
        self._metal_helper.get_node.side_effect = mock_nodes

        self.action.revert()

        mock_nodes[0].set_power_state.assert_called_once_with(
            m_constants.PowerState.ON.value)
