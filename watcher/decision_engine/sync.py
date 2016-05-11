# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

from watcher._i18n import _LI
from watcher.common import context
from watcher.decision_engine.strategy.loading import default
from watcher import objects

LOG = log.getLogger(__name__)


class Syncer(object):
    """Syncs all available goals and strategies with the Watcher DB"""

    def __init__(self):
        self.ctx = context.make_context()
        self._discovered_map = None

        self._available_goals = None
        self._available_goals_map = None

        self._available_strategies = None
        self._available_strategies_map = None

        # This goal mapping maps stale goal IDs to the synced goal
        self.goal_mapping = dict()
        # This strategy mapping maps stale strategy IDs to the synced goal
        self.strategy_mapping = dict()

    @property
    def available_goals(self):
        if self._available_goals is None:
            self._available_goals = objects.Goal.list(self.ctx)
        return self._available_goals

    @property
    def available_strategies(self):
        if self._available_strategies is None:
            self._available_strategies = objects.Strategy.list(self.ctx)
        return self._available_strategies

    @property
    def available_goals_map(self):
        if self._available_goals_map is None:
            self._available_goals_map = {
                g: {"name": g.name, "display_name": g.display_name}
                for g in self.available_goals
            }
        return self._available_goals_map

    @property
    def available_strategies_map(self):
        if self._available_strategies_map is None:
            goals_map = {g.id: g.name for g in self.available_goals}
            self._available_strategies_map = {
                s: {"name": s.name, "goal_name": goals_map[s.goal_id],
                    "display_name": s.display_name}
                for s in self.available_strategies
            }
        return self._available_strategies_map

    def sync(self):
        discovered_map = self.discover()
        goals_map = discovered_map["goals"]
        strategies_map = discovered_map["strategies"]

        for goal_name, goal_map in goals_map.items():
            if goal_map in self.available_goals_map.values():
                LOG.info(_LI("Goal %s already exists"), goal_name)
                continue

            self.goal_mapping.update(self._sync_goal(goal_map))

        for strategy_name, strategy_map in strategies_map.items():
            if strategy_map in self.available_strategies_map.values():
                LOG.info(_LI("Strategy %s already exists"), strategy_name)
                continue

            self.strategy_mapping.update(self._sync_strategy(strategy_map))

        # TODO(v-francoise): Sync the audit templates

    def _sync_goal(self, goal_map):
        goal_name = goal_map['name']
        goal_display_name = goal_map['display_name']
        goal_mapping = dict()

        matching_goals = [g for g in self.available_goals
                          if g.name == goal_name]
        stale_goals = self.soft_delete_stale_goals(goal_map, matching_goals)

        if stale_goals or not matching_goals:
            goal = objects.Goal(self.ctx)
            goal.name = goal_name
            goal.display_name = goal_display_name
            goal.create()
            LOG.info(_LI("Goal %s created"), goal_name)

            # Updating the internal states
            self.available_goals_map[goal] = goal_map
            # Map the old goal IDs to the new (equivalent) goal
            for matching_goal in matching_goals:
                goal_mapping[matching_goal.id] = goal

        return goal_mapping

    def _sync_strategy(self, strategy_map):
        strategy_name = strategy_map['name']
        strategy_display_name = strategy_map['display_name']
        goal_name = strategy_map['goal_name']
        strategy_mapping = dict()

        matching_strategies = [s for s in self.available_strategies
                               if s.name == strategy_name]
        stale_strategies = self.soft_delete_stale_strategies(
            strategy_map, matching_strategies)

        if stale_strategies or not matching_strategies:
            strategy = objects.Strategy(self.ctx)
            strategy.name = strategy_name
            strategy.display_name = strategy_display_name
            strategy.goal_id = objects.Goal.get_by_name(self.ctx, goal_name).id
            strategy.create()
            LOG.info(_LI("Strategy %s created"), strategy_name)

            # Updating the internal states
            self.available_strategies_map[strategy] = strategy_map
            # Map the old strategy IDs to the new (equivalent) strategy
            for matching_strategy in matching_strategies:
                strategy_mapping[matching_strategy.id] = strategy

        return strategy_mapping

    def discover(self):
        strategies_map = {}
        goals_map = {}
        discovered_map = {"goals": goals_map, "strategies": strategies_map}
        strategy_loader = default.DefaultStrategyLoader()
        implemented_strategies = strategy_loader.list_available()

        for _, strategy_cls in implemented_strategies.items():
            goals_map[strategy_cls.get_goal_name()] = {
                "name": strategy_cls.get_goal_name(),
                "display_name":
                    strategy_cls.get_translatable_goal_display_name()}

            strategies_map[strategy_cls.get_name()] = {
                "name": strategy_cls.get_name(),
                "goal_name": strategy_cls.get_goal_name(),
                "display_name": strategy_cls.get_translatable_display_name()}

        return discovered_map

    def soft_delete_stale_goals(self, goal_map, matching_goals):
        goal_name = goal_map['name']
        goal_display_name = goal_map['display_name']

        stale_goals = []
        for matching_goal in matching_goals:
            if matching_goal.display_name == goal_display_name:
                LOG.info(_LI("Goal %s unchanged"), goal_name)
            else:
                LOG.info(_LI("Goal %s modified"), goal_name)
                matching_goal.soft_delete()
                stale_goals.append(matching_goal)

        return stale_goals

    def soft_delete_stale_strategies(self, strategy_map, matching_strategies):
        strategy_name = strategy_map['name']
        strategy_display_name = strategy_map['display_name']

        stale_strategies = []
        for matching_strategy in matching_strategies:
            if matching_strategy.display_name == strategy_display_name:
                LOG.info(_LI("Strategy %s unchanged"), strategy_name)
            else:
                LOG.info(_LI("Strategy %s modified"), strategy_name)
                matching_strategy.soft_delete()
                stale_strategies.append(matching_strategy)

        return stale_strategies
