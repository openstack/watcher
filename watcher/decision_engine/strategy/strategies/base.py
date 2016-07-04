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

from watcher.common import clients
from watcher.common.loader import loadable
from watcher.common import utils
from watcher.decision_engine.loading import default as loading
from watcher.decision_engine.solution import default
from watcher.decision_engine.strategy.common import level
from watcher.metrics_engine.cluster_model_collector import manager


@six.add_metaclass(abc.ABCMeta)
class BaseStrategy(loadable.Loadable):
    """A base class for all the strategies

    A Strategy is an algorithm implementation which is able to find a
    Solution for a given Goal.
    """

    def __init__(self, config, osc=None):
        """Constructor: the signature should be identical within the subclasses

        :param config: Configuration related to this plugin
        :type config: :py:class:`~.Struct`
        :param osc: An OpenStackClients instance
        :type osc: :py:class:`~.OpenStackClients` instance
        """
        super(BaseStrategy, self).__init__(config)
        self._name = self.get_name()
        self._display_name = self.get_display_name()
        self._goal = self.get_goal()
        # default strategy level
        self._strategy_level = level.StrategyLevel.conservative
        self._cluster_state_collector = None
        # the solution given by the strategy
        self._solution = default.DefaultSolution(goal=self.goal, strategy=self)
        self._osc = osc
        self._collector_manager = None
        self._model = None
        self._goal = None
        self._input_parameters = utils.Struct()

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
        """The goal name the strategy achieves"""
        raise NotImplementedError()

    @classmethod
    def get_goal(cls):
        """The goal the strategy achieves"""
        goal_loader = loading.DefaultGoalLoader()
        return goal_loader.load(cls.get_goal_name())

    @classmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        return []

    @abc.abstractmethod
    def pre_execute(self):
        """Pre-execution phase

        This can be used to fetch some pre-requisites or data.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def do_execute(self):
        """Strategy execution phase

        This phase is where you should put the main logic of your strategy.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        raise NotImplementedError()

    def execute(self):
        """Execute a strategy

        :return: A computed solution (via a placement algorithm)
        :rtype: :py:class:`~.BaseSolution` instance
        """
        self.pre_execute()
        self.do_execute()
        self.post_execute()

        self.solution.compute_global_efficacy()

        return self.solution

    @property
    def collector(self):
        if self._collector_manager is None:
            self._collector_manager = manager.CollectorManager()
        return self._collector_manager

    @property
    def model(self):
        """Cluster data model

        :returns: Cluster data model the strategy is executed on
        :rtype model: :py:class:`~.ModelRoot` instance
        """
        if self._model is None:
            collector = self.collector.get_cluster_model_collector(
                osc=self.osc)
            self._model = collector.get_latest_cluster_data_model()

        return self._model

    @classmethod
    def get_schema(cls):
        """Defines a Schema that the input parameters shall comply to

        :return: A jsonschema format (mandatory default setting)
        :rtype: dict
        """
        return {}

    @property
    def input_parameters(self):
        return self._input_parameters

    @input_parameters.setter
    def input_parameters(self, p):
        self._input_parameters = p

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

    @property
    def display_name(self):
        return self._display_name

    @property
    def goal(self):
        return self._goal

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
        return "dummy"


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
        return "unclassified"


@six.add_metaclass(abc.ABCMeta)
class ServerConsolidationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "server_consolidation"


@six.add_metaclass(abc.ABCMeta)
class ThermalOptimizationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "thermal_optimization"


@six.add_metaclass(abc.ABCMeta)
class WorkloadStabilizationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "workload_balancing"
