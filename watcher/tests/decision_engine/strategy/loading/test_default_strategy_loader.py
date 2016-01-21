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
from stevedore import extension
from watcher.common import exception
from watcher.decision_engine.strategy.loading import default as default_loading
from watcher.decision_engine.strategy.strategies import dummy_strategy
from watcher.tests import base


class TestDefaultStrategyLoader(base.TestCase):

    strategy_loader = default_loading.DefaultStrategyLoader()

    def test_load_strategy_with_empty_model(self):
        self.assertRaises(
            exception.LoadingError, self.strategy_loader.load, None)

    def test_load_strategy_is_basic(self):
        exptected_strategy = 'basic'
        selected_strategy = self.strategy_loader.load(exptected_strategy)
        self.assertEqual(
            selected_strategy.name,
            exptected_strategy,
            'The default strategy should be basic')

    @patch("watcher.common.loader.default.ExtensionManager")
    def test_strategy_loader(self, m_extension_manager):
        dummy_strategy_name = "dummy"
        # Set up the fake Stevedore extensions
        m_extension_manager.return_value = extension.\
            ExtensionManager.make_test_instance(
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
        strategy_loader = default_loading.DefaultStrategyLoader()
        loaded_strategy = strategy_loader.load("dummy")

        self.assertEqual("dummy", loaded_strategy.name)
        self.assertEqual("Dummy Strategy", loaded_strategy.description)

    def test_load_dummy_strategy(self):
        strategy_loader = default_loading.DefaultStrategyLoader()
        loaded_strategy = strategy_loader.load("dummy")
        self.assertIsInstance(loaded_strategy, dummy_strategy.DummyStrategy)

        def test_endpoints(self):
            for endpoint in self.strategy_loader.list_available():
                self.assertIsNotNone(self.strategy_loader.load(endpoint))
