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
        self._available_goal_names = None
        self._available_goals_map = None

    @property
    def available_goals(self):
        if self._available_goals is None:
            self._available_goals = objects.Goal.list(self.ctx)
        return self._available_goals

    @property
    def available_goal_names(self):
        if self._available_goal_names is None:
            self._available_goal_names = [g.name for g in self.available_goals]
        return self._available_goal_names

    @property
    def available_goals_map(self):
        if self._available_goals_map is None:
            self._available_goals_map = {
                g: {"name": g.name, "display_name": g.display_name}
                for g in self.available_goals
            }
        return self._available_goals_map

    def sync(self):
        discovered_map = self.discover()
        goals_map = discovered_map["goals"]

        for goal_name, goal_map in goals_map.items():
            if goal_map in self.available_goals_map.values():
                LOG.info(_LI("Goal %s already exists"), goal_name)
                continue

            self._sync_goal(goal_map)

    def _sync_goal(self, goal_map):
        goal_name = goal_map['name']
        goal_display_name = goal_map['display_name']

        matching_goals = [g for g in self.available_goals
                          if g.name == goal_name]
        stale_goals = self.soft_delete_stale_goals(goal_map, matching_goals)

        if stale_goals or not matching_goals:
            goal = objects.Goal(self.ctx)
            goal.name = goal_name
            goal.display_name = goal_display_name
            goal.create()
            LOG.info(_LI("Goal %s created"), goal_name)
            self.available_goal_names.append(goal_name)
            self.available_goals_map[goal] = goal_map
            # We have to update the audit templates that were pointing
            # self._sync_audit_templates(stale_goals, goal)

    # def _sync_audit_templates(self, stale_goals, goal):
    #     related_audit_templates = []
    #     for stale_goal in stale_goals:
    #         filters = {"goal_id": stale_goal.id}
    #         related_audit_templates.extend(
    #             objects.AuditTemplate.list(self.ctx, filters=filters))

    #     for audit_template in related_audit_templates:
    #         LOG.info(_LI("Audit Template '%s' updated with synced goal"))
    #         audit_template.goal_id = goal.id
    #         audit_template.save()

    def discover(self):
        strategies_map = {}
        goals_map = {}
        discovered_map = {"goals": goals_map, "strategies": strategies_map}
        strategy_loader = default.DefaultStrategyLoader()
        implemented_strategies = strategy_loader.list_available()

        # TODO(v-francoise): At this point I only register the goals, but later
        # on this will be extended to also populate the strategies map.
        for _, strategy_cls in implemented_strategies.items():
            # This mapping is a temporary trick where I use the strategy
            # DEFAULT_NAME as the goal name because we used to have a 1-to-1
            # mapping between the goal and the strategy.
            # TODO(v-francoise): Dissociate the goal name and the strategy name
            goals_map[strategy_cls.DEFAULT_NAME] = {
                "name": strategy_cls.DEFAULT_NAME,
                "display_name": strategy_cls.DEFAULT_DESCRIPTION}

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
