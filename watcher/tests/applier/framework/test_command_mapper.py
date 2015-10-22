# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
from watcher.applier.framework.default_command_mapper import \
    DefaultCommandMapper
from watcher.decision_engine.framework.default_planner import Primitives
from watcher.tests import base


class TestCommandMapper(base.TestCase):
    def setUp(self):
        super(TestCommandMapper, self).setUp()
        self.mapper = DefaultCommandMapper()

    def test_build_command_cold(self):
        action = mock.MagicMock()
        action.action_type = Primitives.COLD_MIGRATE.value
        cmd = self.mapper.build_primitive_command(action)
        self.assertIsNotNone(cmd)

    def test_build_command_live(self):
        action = mock.MagicMock()
        action.action_type = Primitives.LIVE_MIGRATE.value
        cmd = self.mapper.build_primitive_command(action)
        self.assertIsNotNone(cmd)

    def test_build_command_h_s(self):
        action = mock.MagicMock()
        action.action_type = Primitives.HYPERVISOR_STATE.value
        cmd = self.mapper.build_primitive_command(action)
        self.assertIsNotNone(cmd)

    def test_build_command_p_s(self):
        action = mock.MagicMock()
        action.action_type = Primitives.POWER_STATE.value
        cmd = self.mapper.build_primitive_command(action)
        self.assertIsNotNone(cmd)

    def test_build_command_exception_attribute(self):
        action = mock.MagicMock
        self.assertRaises(AttributeError, self.mapper.build_primitive_command,
                          action)
