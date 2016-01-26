# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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
import voluptuous

from watcher.applier.actions import base as baction
from watcher.applier.actions import change_nova_service_state
from watcher.decision_engine.model import hypervisor_state as hstate
from watcher.tests import base


class TestChangeNovaServiceState(base.TestCase):
    def setUp(self):
        super(TestChangeNovaServiceState, self).setUp()
        self.a = change_nova_service_state.ChangeNovaServiceState()

    def test_parameters_down(self):
        self.a.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.a.STATE: hstate.HypervisorState.OFFLINE.value}
        self.assertEqual(True, self.a.validate_parameters())

    def test_parameters_up(self):
        self.a.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.a.STATE: hstate.HypervisorState.ONLINE.value}
        self.assertEqual(True, self.a.validate_parameters())

    def test_parameters_exception_wrong_state(self):
        self.a.input_parameters = {
            baction.BaseAction.RESOURCE_ID: "compute-1",
            self.a.STATE: 'error'}
        self.assertRaises(voluptuous.Invalid, self.a.validate_parameters)

    def test_parameters_resource_id_empty(self):
        self.a.input_parameters = {
            self.a.STATE: None}
        self.assertRaises(voluptuous.Invalid, self.a.validate_parameters)

    def test_parameters_applies_add_extra(self):
        self.a.input_parameters = {"extra": "failed"}
        self.assertRaises(voluptuous.Invalid, self.a.validate_parameters)
