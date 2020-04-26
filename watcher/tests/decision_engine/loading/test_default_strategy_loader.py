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

from stevedore import extension
from unittest import mock

from watcher.common import exception
from watcher.decision_engine.loading import default as default_loading
from watcher.decision_engine.strategy.strategies import dummy_strategy
from watcher.tests import base


class TestDefaultStrategyLoader(base.TestCase):

    def setUp(self):
        super(TestDefaultStrategyLoader, self).setUp()
        self.strategy_loader = default_loading.DefaultStrategyLoader()

    def test_load_strategy_with_empty_model(self):
        self.assertRaises(
            exception.LoadingError, self.strategy_loader.load, None)

    def test_strategy_loader(self):
        dummy_strategy_name = "dummy"
        # Set up the fake Stevedore extensions
        fake_extmanager_call = extension.ExtensionManager.make_test_instance(
            extensions=[extension.Extension(
                name=dummy_strategy_name,
                entry_point="%s:%s" % (
                    dummy_strategy.DummyStrategy.__module__,
                    dummy_strategy.DummyStrategy.__name__),
                plugin=dummy_strategy.DummyStrategy,
                obj=None,
            )],
            namespace="watcher_strategies",
        )

        with mock.patch.object(extension, "ExtensionManager") as m_ext_manager:
            m_ext_manager.return_value = fake_extmanager_call
            loaded_strategy = self.strategy_loader.load(
                "dummy")

        self.assertEqual("dummy", loaded_strategy.name)
        self.assertEqual("Dummy strategy", loaded_strategy.display_name)

    def test_load_dummy_strategy(self):
        strategy_loader = default_loading.DefaultStrategyLoader()
        loaded_strategy = strategy_loader.load("dummy")
        self.assertIsInstance(loaded_strategy, dummy_strategy.DummyStrategy)


class TestLoadStrategiesWithDefaultStrategyLoader(base.TestCase):

    strategy_loader = default_loading.DefaultStrategyLoader()

    scenarios = [
        (strategy_name,
         {"strategy_name": strategy_name, "strategy_cls": strategy_cls})
        for strategy_name, strategy_cls
        in strategy_loader.list_available().items()]

    def test_load_strategies(self):
        strategy = self.strategy_loader.load(self.strategy_name)
        self.assertIsNotNone(strategy)
        self.assertEqual(self.strategy_name, strategy.name)
