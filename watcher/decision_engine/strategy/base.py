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
from watcher.decision_engine.solution.default import DefaultSolution
from watcher.decision_engine.strategy.level import StrategyLevel


LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseStrategy(object):
    """A Strategy is an algorithm implementation which is able to find a
    Solution for a given Goal.
    """

    def __init__(self, name=None, description=None):
        self._name = name
        self.description = description
        # default strategy level
        self._strategy_level = StrategyLevel.conservative
        self._cluster_state_collector = None
        # the solution given by the strategy
        self._solution = DefaultSolution()

    @abc.abstractmethod
    def execute(self, model):
        """Execute a strategy

        :param model: The name of the strategy to execute (loaded dynamically)
        :type model: str
        :return: A computed solution (via a placement algorithm)
        :rtype: :class:`watcher.decision_engine.solution.base.Solution`
        """

    @property
    def solution(self):
        return self._solution

    @solution.setter
    def solution(self, s):
        self._solution = s

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, n):
        self._name = n

    @property
    def strategy_level(self):
        return self._strategy_level

    @strategy_level.setter
    def strategy_level(self, s):
        self._strategy_level = s

    @property
    def state_collector(self):
        return self._cluster_state_collector

    @state_collector.setter
    def state_collector(self, s):
        self._cluster_state_collector = s
