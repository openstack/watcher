# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

import abc
from oslo_log import log

import six
from watcher.decision_engine.api.strategy.strategy_level import StrategyLevel
from watcher.decision_engine.framework.default_solution import DefaultSolution


LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Strategy(object):
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description
        # default strategy level
        self.strategy_level = StrategyLevel.conservative
        self.metrics_collector = None
        self.cluster_state_collector = None
        # the solution given by the strategy
        self.solution = DefaultSolution()

    def get_solution(self):
        return self.solution

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def get_strategy_strategy_level(self):
        return self.strategy_level

    def set_strategy_strategy_level(self, strategy_level):
        """Convervative to Aggressive

        the aims is to minimize le number of migrations
        :param threshold:
        """
        self.strategy_level = strategy_level

    @abc.abstractmethod
    def execute(self, model):
        """Execute a strategy

        :param model:
        :return:
        """

    def get_metrics_resource_collector(self):
        return self.metrics_collector

    def get_cluster_state_collector(self):
        return self.cluster_state_collector

    def set_metrics_resource_collector(self, metrics_collector):
        self.metrics_collector = metrics_collector

    def set_cluster_state_collector(self, cluster_state_collector):
        self.cluster_state_collector = cluster_state_collector
