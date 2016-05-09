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

:ref:`Some default implementations are provided <watcher_strategies>`, but it
is possible to :ref:`develop new implementations <implement_strategy_plugin>`
which are dynamically loaded by Watcher at launch time.
"""

import abc
import six

from watcher._i18n import _
from watcher.common import clients
from watcher.common.loader import loadable
from watcher.decision_engine.solution import default
from watcher.decision_engine.strategy.common import level


@six.add_metaclass(abc.ABCMeta)
class BaseStrategy(loadable.Loadable):
    """A base class for all the strategies

    A Strategy is an algorithm implementation which is able to find a
    Solution for a given Goal.
    """

    def __init__(self, config, osc=None):
        """:param osc: an OpenStackClients instance"""
        super(BaseStrategy, self).__init__(config)
        self._name = self.get_name()
        self._display_name = self.get_display_name()
        # default strategy level
        self._strategy_level = level.StrategyLevel.conservative
        self._cluster_state_collector = None
        # the solution given by the strategy
        self._solution = default.DefaultSolution()
        self._osc = osc

    @classmethod
    @abc.abstractmethod
    def get_name(cls):
        """The name of the strategy"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_display_name(cls):
        """The goal display name for the strategy"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_translatable_display_name(cls):
        """The translatable msgid of the strategy"""
        # Note(v-francoise): Defined here to be used as the translation key for
        # other services
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_goal_name(cls):
        """The goal name for the strategy"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_goal_display_name(cls):
        """The translated display name related to the goal of the strategy"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_translatable_goal_display_name(cls):
        """The translatable msgid related to the goal of the strategy"""
        # Note(v-francoise): Defined here to be used as the translation key for
        # other services
        raise NotImplementedError()

    @classmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        return []

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
    def id(self):
        return self._name

    @property
    def display_name(self):
        return self._display_name

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


@six.add_metaclass(abc.ABCMeta)
class DummyBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "DUMMY"

    @classmethod
    def get_goal_display_name(cls):
        return _("Dummy goal")

    @classmethod
    def get_translatable_goal_display_name(cls):
        return "Dummy goal"


@six.add_metaclass(abc.ABCMeta)
class UnclassifiedStrategy(BaseStrategy):
    """This base class is used to ease the development of new strategies

    The goal defined within this strategy can be used to simplify the
    documentation explaining how to implement a new strategy plugin by
    ommitting the need for the strategy developer to define a goal straight
    away.
    """

    @classmethod
    def get_goal_name(cls):
        return "UNCLASSIFIED"

    @classmethod
    def get_goal_display_name(cls):
        return _("Unclassified")

    @classmethod
    def get_translatable_goal_display_name(cls):
        return "Unclassified"


@six.add_metaclass(abc.ABCMeta)
class ServerConsolidationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "SERVER_CONSOLIDATION"

    @classmethod
    def get_goal_display_name(cls):
        return _("Server consolidation")

    @classmethod
    def get_translatable_goal_display_name(cls):
        return "Server consolidation"


@six.add_metaclass(abc.ABCMeta)
class ThermalOptimizationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "THERMAL_OPTIMIZATION"

    @classmethod
    def get_goal_display_name(cls):
        return _("Thermal optimization")

    @classmethod
    def get_translatable_goal_display_name(cls):
        return "Thermal optimization"


@six.add_metaclass(abc.ABCMeta)
class WorkloadStabilizationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "WORKLOAD_BALANCING"

    @classmethod
    def get_goal_display_name(cls):
        return _("Workload balancing")

    @classmethod
    def get_translatable_goal_display_name(cls):
        return "Workload balancing"
