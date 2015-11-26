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
from mock import patch
from oslo_config import cfg
from watcher.common.exception import WatcherException
from watcher.decision_engine.strategy.loader import StrategyLoader
from watcher.decision_engine.strategy.selector.default import StrategySelector
from watcher.tests.base import TestCase
CONF = cfg.CONF


class TestStrategySelector(TestCase):

    strategy_selector = StrategySelector()

    @patch.object(StrategyLoader, 'load')
    def test_define_from_goal(self, mock_call):
        cfg.CONF.set_override(
            'goals', {"DUMMY": "fake"}, group='watcher_goals'
        )
        expected_goal = 'DUMMY'
        expected_strategy = CONF.watcher_goals.goals[expected_goal]
        self.strategy_selector.define_from_goal(expected_goal)
        mock_call.assert_called_once_with(expected_strategy)

    @patch.object(StrategyLoader, 'load')
    def test_define_from_goal_with_incorrect_mapping(self, mock_call):
        cfg.CONF.set_override(
            'goals', {}, group='watcher_goals'
        )
        self.assertRaises(
            WatcherException,
            self.strategy_selector.define_from_goal,
            "DUMMY"
        )
        self.assertEqual(mock_call.call_count, 0)
