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

"""
A :ref:`Strategy <strategy_definition>` is an algorithm implementation which is
able to find a :ref:`Solution <solution_definition>` for a given
:ref:`Goal <goal_definition>`.

There may be several potential strategies which are able to achieve the same
:ref:`Goal <goal_definition>`. This is why it is possible to configure which
specific :ref:`Strategy <strategy_definition>` should be used for each
:ref:`Goal <goal_definition>`.

Some strategies may provide better optimization results but may take more time
to find an optimal :ref:`Solution <solution_definition>`.

When a new :ref:`Goal <goal_definition>` is added to the Watcher configuration,
at least one default associated :ref:`Strategy <strategy_definition>` should be
provided as well.
"""

import abc

from oslo_log import log
import six

from watcher.common import clients
from watcher.decision_engine.solution import default
from watcher.decision_engine.strategy.common import level

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseStrategy(object):
    """A base class for all the strategies

    A Strategy is an algorithm implementation which is able to find a
    Solution for a given Goal.
    """

    def __init__(self, name=None, description=None, osc=None):
        """:param osc: an OpenStackClients instance"""
        self._name = name
        self.description = description
        # default strategy level
        self._strategy_level = level.StrategyLevel.conservative
        self._cluster_state_collector = None
        # the solution given by the strategy
        self._solution = default.DefaultSolution()
        self._osc = osc

    @abc.abstractmethod
    def execute(self, original_model):
        """Execute a strategy

        :param original_model: The model the strategy is executed on
        :type model: str
        :return: A computed solution (via a placement algorithm)
        :rtype: :class:`watcher.decision_engine.solution.base.BaseSolution`
        """

    @property
    def osc(self):
        if not self._osc:
            self._osc = clients.OpenStackClients()
        return self._osc

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
