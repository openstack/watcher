# -*- encoding: utf-8 -*-
# Copyright (c) 2017 b<>com
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

import mock

from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestActuator(TestBaseStrategy):

    def setUp(self):
        super(TestActuator, self).setUp()
        self.strategy = strategies.Actuator(config=mock.Mock())

    def test_actuator_strategy(self):
        fake_action = {"action_type": "TEST", "input_parameters": {"a": "b"}}
        self.strategy.input_parameters = utils.Struct(
            {"actions": [fake_action]})
        solution = self.strategy.execute()
        self.assertEqual(1, len(solution.actions))
        self.assertEqual([fake_action], solution.actions)
