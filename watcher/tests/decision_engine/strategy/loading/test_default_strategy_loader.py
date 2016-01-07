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
from __future__ import unicode_literals

from mock import patch
from stevedore.extension import Extension
from stevedore.extension import ExtensionManager

from watcher.decision_engine.strategy.loading.default import \
    DefaultStrategyLoader
from watcher.decision_engine.strategy.strategies.base import BaseStrategy
from watcher.decision_engine.strategy.strategies.dummy_strategy import \
    DummyStrategy
from watcher.tests.base import TestCase


class TestDefaultStrategyLoader(TestCase):

    strategy_loader = DefaultStrategyLoader()

    def test_load_strategy_with_empty_model(self):
        selected_strategy = self.strategy_loader.load(None)
        self.assertIsNotNone(selected_strategy,
                             'The default strategy not be must none')
        self.assertIsInstance(selected_strategy, BaseStrategy)

    def test_load_strategy_is_basic(self):
        exptected_strategy = 'basic'
        selected_strategy = self.strategy_loader.load(exptected_strategy)
        self.assertEqual(
            selected_strategy.name,
            exptected_strategy,
            'The default strategy should be basic')

    @patch(
        "watcher.decision_engine.strategy.loading.default.ExtensionManager")
    def test_strategy_loader(self, m_extension_manager):
        dummy_strategy_name = "dummy"
        # Set up the fake Stevedore extensions
        m_extension_manager.return_value = ExtensionManager.make_test_instance(
            extensions=[Extension(
                name=dummy_strategy_name,
                entry_point="%s:%s" % (DummyStrategy.__module__,
                                       DummyStrategy.__name__),
                plugin=DummyStrategy,
                obj=None,
            )],
            namespace="watcher_strategies",
        )
        strategy_loader = DefaultStrategyLoader()
        loaded_strategy = strategy_loader.load("dummy")

        self.assertEqual("dummy", loaded_strategy.name)
        self.assertEqual("Dummy Strategy", loaded_strategy.description)

    def test_load_dummy_strategy(self):
        strategy_loader = DefaultStrategyLoader()
        loaded_strategy = strategy_loader.load("dummy")
        self.assertIsInstance(loaded_strategy, DummyStrategy)

        def test_endpoints(self):
            for endpoint in self.strategy_loader.list_available():
                self.assertIsNotNone(self.strategy_loader.load(endpoint))
