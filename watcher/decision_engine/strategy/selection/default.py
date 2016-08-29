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

from oslo_log import log

from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.loading import default
from watcher.decision_engine.strategy.selection import base

LOG = log.getLogger(__name__)


class DefaultStrategySelector(base.BaseSelector):

    def __init__(self, goal_name, strategy_name=None, osc=None):
        """Default strategy selector

        :param goal_name: Name of the goal
        :param strategy_name: Name of the strategy
        :param osc: an OpenStackClients instance
        """
        super(DefaultStrategySelector, self).__init__()
        self.goal_name = goal_name
        self.strategy_name = strategy_name
        self.osc = osc
        self.strategy_loader = default.DefaultStrategyLoader()

    def select(self):
        """Selects a strategy

        :raises: :py:class:`~.LoadingError` if it failed to load a strategy
        :returns: A :py:class:`~.BaseStrategy` instance
        """
        strategy_to_load = None
        try:
            if self.strategy_name:
                strategy_to_load = self.strategy_name
            else:
                available_strategies = self.strategy_loader.list_available()
                available_strategies_for_goal = list(
                    key for key, strat in available_strategies.items()
                    if strat.get_goal_name() == self.goal_name)

                if not available_strategies_for_goal:
                    raise exception.NoAvailableStrategyForGoal(
                        goal=self.goal_name)

                # TODO(v-francoise): We should do some more work here to select
                # a strategy out of a given goal instead of just choosing the
                # 1st one
                strategy_to_load = available_strategies_for_goal[0]
            return self.strategy_loader.load(strategy_to_load, osc=self.osc)
        except exception.NoAvailableStrategyForGoal:
            raise
        except Exception as exc:
            LOG.exception(exc)
            raise exception.LoadingError(
                _("Could not load any strategy for goal %(goal)s"),
                goal=self.goal_name)
