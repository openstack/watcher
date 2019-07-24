# Copyright (c) 2016 b<>com
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

from __future__ import unicode_literals

import jsonschema
import mock

from watcher.applier.actions import base as baction
from watcher.applier.actions import change_nova_service_state
from watcher.common import clients
from watcher.common import nova_helper
from watcher.decision_engine.model import element
from watcher.tests import base


class TestChangeNovaServiceState(base.TestCase):

    def setUp(self):
        super(TestChangeNovaServiceState, self).setUp()

        self.m_osc_cls = mock.Mock()
        self.m_helper_cls = mock.Mock()
        self.m_helper = mock.Mock(spec=nova_helper.NovaHelper)
        self.m_helper_cls.return_value = self.m_helper
        self.m_osc = mock.Mock(spec=clients.OpenStackClients)
        self.m_osc_cls.return_value = self.m_osc

        m_openstack_clients = mock.patch.object(
            clients, "OpenStackClients", self.m_osc_cls)
        m_nova_helper = mock.patch.object(
            nova_helper, "NovaHelper", self.m_helper_cls)

        m_openstack_clients.start()
        m_nova_helper.start()

        self.addCleanup(m_openstack_clients.stop)
        self.addCleanup(m_nova_helper.stop)

        self.input_parameters = {
            "resource_name": "compute-1",
            "state": element.ServiceState.ENABLED.value,
        }
        self.action = change_nova_service_state.ChangeNovaServiceState(
            mock.Mock())
        self.action.input_parameters = self.input_parameters

    def test_parameters_down(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.action.STATE: element.ServiceState.DISABLED.value}
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_up(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.action.STATE: element.ServiceState.ENABLED.value}
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_exception_wrong_state(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.action.STATE: 'error'}
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_resource_id_empty(self):
        self.action.input_parameters = {
            self.action.STATE: element.ServiceState.ENABLED.value,
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

    def test_change_service_state_post_condition(self):
        try:
            self.action.post_condition()
        except Exception as exc:
            self.fail(exc)

    def test_execute_change_service_state_with_enable_target(self):
        self.action.execute()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.enable_service_nova_compute.assert_called_once_with(
            "compute-1")

    def test_execute_change_service_state_with_disable_target(self):
        self.action.input_parameters["state"] = (
            element.ServiceState.DISABLED.value)
        self.action.input_parameters["disabled_reason"] = (
            "watcher_disabled")
        self.action.execute()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.disable_service_nova_compute.assert_called_once_with(
            "compute-1", "watcher_disabled")

    def test_revert_change_service_state_with_enable_target(self):
        self.action.input_parameters["disabled_reason"] = (
            "watcher_disabled")
        self.action.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.disable_service_nova_compute.assert_called_once_with(
            "compute-1", "watcher_disabled")

    def test_revert_change_service_state_with_disable_target(self):
        self.action.input_parameters["state"] = (
            element.ServiceState.DISABLED.value)
        self.action.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.enable_service_nova_compute.assert_called_once_with(
            "compute-1")
