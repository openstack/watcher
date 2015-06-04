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
import mock
from oslo_config import cfg
from watcher.decision_engine.framework.strategy.strategy_loader import \
    StrategyLoader
from watcher.decision_engine.framework.strategy.strategy_selector import \
    StrategySelector
from watcher.objects.audit_template import Goal
from watcher.tests import base

CONF = cfg.CONF


class TestStrategySelector(base.BaseTestCase):

    strategy_selector = StrategySelector()

    def test_define_from_with_empty(self):
        expected_goal = None
        expected_strategy = \
            CONF.watcher_goals.goals[Goal.SERVERS_CONSOLIDATION]
        with mock.patch.object(StrategyLoader, 'load') as \
                mock_call:
                self.strategy_selector.define_from_goal(expected_goal)
                mock_call.assert_called_once_with(expected_strategy)

    def test_define_from_goal(self):
        expected_goal = Goal.BALANCE_LOAD
        expected_strategy = CONF.watcher_goals.goals[expected_goal]
        with mock.patch.object(StrategyLoader, 'load') as \
                mock_call:
                self.strategy_selector.define_from_goal(expected_goal)
                mock_call.assert_called_once_with(expected_strategy)
