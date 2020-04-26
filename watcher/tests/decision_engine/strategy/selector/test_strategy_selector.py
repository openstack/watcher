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

from unittest import mock

from watcher.common import exception
from watcher.decision_engine.loading import default as default_loader
from watcher.decision_engine.strategy.selection import (
    default as default_selector)
from watcher.decision_engine.strategy import strategies
from watcher.tests import base


class TestStrategySelector(base.TestCase):

    @mock.patch.object(default_loader.DefaultStrategyLoader, 'load')
    def test_select_with_strategy_name(self, m_load):
        expected_goal = 'dummy'
        expected_strategy = "dummy"
        strategy_selector = default_selector.DefaultStrategySelector(
            expected_goal, expected_strategy, osc=None)
        strategy_selector.select()
        m_load.assert_called_once_with(expected_strategy, osc=None)

    @mock.patch.object(default_loader.DefaultStrategyLoader, 'load')
    @mock.patch.object(default_loader.DefaultStrategyLoader, 'list_available')
    def test_select_with_goal_name_only(self, m_list_available, m_load):
        m_list_available.return_value = {"dummy": strategies.DummyStrategy}
        expected_goal = 'dummy'
        expected_strategy = "dummy"
        strategy_selector = default_selector.DefaultStrategySelector(
            expected_goal, osc=None)
        strategy_selector.select()
        m_load.assert_called_once_with(expected_strategy, osc=None)

    def test_select_non_existing_strategy(self):
        strategy_selector = default_selector.DefaultStrategySelector(
            "dummy", "NOT_FOUND")
        self.assertRaises(exception.LoadingError, strategy_selector.select)

    @mock.patch.object(default_loader.DefaultStrategyLoader, 'list_available')
    def test_select_no_available_strategy_for_goal(self, m_list_available):
        m_list_available.return_value = {}
        strategy_selector = default_selector.DefaultStrategySelector("dummy")
        self.assertRaises(exception.NoAvailableStrategyForGoal,
                          strategy_selector.select)
