# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
from mock import MagicMock
from mock import patch

from watcher.decision_engine.solution.default import DefaultSolution
from watcher.decision_engine.strategy.context.default import \
    DefaultStrategyContext
from watcher.decision_engine.strategy.selection.default import \
    DefaultStrategySelector
from watcher.decision_engine.strategy.strategies.dummy_strategy import \
    DummyStrategy
from watcher.tests import base


class TestStrategyContext(base.BaseTestCase):
    strategy_context = DefaultStrategyContext()

    @patch.object(DefaultStrategySelector, 'define_from_goal')
    def test_execute_strategy(self, mock_call):
        mock_call.return_value = DummyStrategy()
        cluster_data_model = MagicMock()
        solution = self.strategy_context.execute_strategy("dummy",
                                                          cluster_data_model)
        self.assertIsInstance(solution, DefaultSolution)
