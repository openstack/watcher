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

from watcher.decision_engine.api.strategy.strategy_context import \
    StrategyContext
from watcher.decision_engine.framework.default_planner import DefaultPlanner
from watcher.decision_engine.framework.strategy.strategy_selector import \
    StrategySelector
from watcher.openstack.common import log

LOG = log.getLogger(__name__)


class StrategyContextImpl(StrategyContext):
    def __init__(self, broker=None):
        LOG.debug("Initializing decision_engine Engine API ")
        self.strategies = {}
        self.selected_strategies = []
        self.broker = broker
        self.planner = DefaultPlanner()
        self.strategy_selector = StrategySelector()
        self.goal = None
        self.metrics_resource_collector = None

    def add_strategy(self, strategy):
        self.strategies[strategy.name] = strategy
        self.selected_strategy = strategy.name

    def remove_strategy(self, strategy):
        pass

    def set_goal(self, goal):
        self.goal = goal

    def set_metrics_resource_collector(self, metrics_resource_collector):
        self.metrics_resource_collector = metrics_resource_collector

    def execute_strategy(self, model):
        # todo(jed) create thread + refactoring
        selected_strategy = self.strategy_selector.define_from_goal(self.goal)
        selected_strategy.set_metrics_resource_collector(
            self.metrics_resource_collector)
        return selected_strategy.execute(model)
