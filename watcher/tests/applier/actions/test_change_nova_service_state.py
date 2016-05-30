# -*- encoding: utf-8 -*-
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

import mock
import voluptuous

from watcher.applier.actions import base as baction
from watcher.applier.actions import change_nova_service_state
from watcher.common import clients
from watcher.common import nova_helper
from watcher.decision_engine.model import hypervisor_state as hstate
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
            baction.BaseAction.RESOURCE_ID: "compute-1",
            "state": hstate.HypervisorState.ENABLED.value,
        }
        self.action = change_nova_service_state.ChangeNovaServiceState(
            mock.Mock())
        self.action.input_parameters = self.input_parameters

    def test_parameters_down(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.action.STATE: hstate.HypervisorState.DISABLED.value}
        self.assertEqual(True, self.action.validate_parameters())

    def test_parameters_up(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.action.STATE: hstate.HypervisorState.ENABLED.value}
        self.assertEqual(True, self.action.validate_parameters())

    def test_parameters_exception_wrong_state(self):
        self.action.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.action.STATE: 'error'}
        exc = self.assertRaises(
            voluptuous.Invalid, self.action.validate_parameters)
        self.assertEqual(
            [(['state'], voluptuous.ScalarInvalid)],
            [([str(p) for p in e.path], type(e)) for e in exc.errors])

    def test_parameters_resource_id_empty(self):
        self.action.input_parameters = {
            self.action.STATE: hstate.HypervisorState.ENABLED.value,
        }
        exc = self.assertRaises(
            voluptuous.Invalid, self.action.validate_parameters)
        self.assertEqual(
            [(['resource_id'], voluptuous.RequiredFieldInvalid)],
            [([str(p) for p in e.path], type(e)) for e in exc.errors])

    def test_parameters_applies_add_extra(self):
        self.action.input_parameters = {"extra": "failed"}
        exc = self.assertRaises(
            voluptuous.Invalid, self.action.validate_parameters)
        self.assertEqual(
            sorted([(['resource_id'], voluptuous.RequiredFieldInvalid),
                    (['state'], voluptuous.RequiredFieldInvalid),
                    (['extra'], voluptuous.Invalid)],
                   key=lambda x: str(x[0])),
            sorted([([str(p) for p in e.path], type(e)) for e in exc.errors],
                   key=lambda x: str(x[0])))

    def test_change_service_state_precondition(self):
        try:
            self.action.precondition()
        except Exception as exc:
            self.fail(exc)

    def test_change_service_state_postcondition(self):
        try:
            self.action.postcondition()
        except Exception as exc:
            self.fail(exc)

    def test_execute_change_service_state_with_enable_target(self):
        self.action.execute()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.enable_service_nova_compute.assert_called_once_with(
            "compute-1")

    def test_execute_change_service_state_with_disable_target(self):
        self.action.input_parameters["state"] = (
            hstate.HypervisorState.DISABLED.value)
        self.action.execute()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.disable_service_nova_compute.assert_called_once_with(
            "compute-1")

    def test_revert_change_service_state_with_enable_target(self):
        self.action.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.disable_service_nova_compute.assert_called_once_with(
            "compute-1")

    def test_revert_change_service_state_with_disable_target(self):
        self.action.input_parameters["state"] = (
            hstate.HypervisorState.DISABLED.value)
        self.action.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.enable_service_nova_compute.assert_called_once_with(
            "compute-1")
