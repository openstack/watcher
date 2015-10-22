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
from watcher.decision_engine.framework.strategy.strategy_loader import \
    StrategyLoader
from watcher.tests import base


class TestStrategySelector(base.BaseTestCase):

    strategy_loader = StrategyLoader()

    def test_load_strategy_with_empty_model(self):
        selected_strategy = self.strategy_loader.load(None)
        self.assertIsNotNone(selected_strategy,
                             'The default strategy be must not none')

    def test_load_strategy_is_basic(self):
        exptected_strategy = 'basic'
        selected_strategy = self.strategy_loader.load(exptected_strategy)
        self.assertEqual(
            selected_strategy.get_name(),
            exptected_strategy,
            'The default strategy should be basic')

    def test_load_driver(self):
        algo = self.strategy_loader.load_driver("basic")
        self.assertEqual(algo._names[0], "basic")
