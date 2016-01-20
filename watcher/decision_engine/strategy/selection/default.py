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

from oslo_config import cfg
from oslo_log import log

from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.strategy.loading import default
from watcher.decision_engine.strategy.selection import base

LOG = log.getLogger(__name__)
CONF = cfg.CONF

default_goals = {'DUMMY': 'dummy'}

WATCHER_GOALS_OPTS = [
    cfg.DictOpt(
        'goals',
        default=default_goals,
        required=True,
        help='Goals used for the optimization. '
             'Maps each goal to an associated strategy (for example: '
             'BASIC_CONSOLIDATION:basic, MY_GOAL:my_strategy_1)'),
]
goals_opt_group = cfg.OptGroup(name='watcher_goals',
                               title='Goals available for the optimization')
CONF.register_group(goals_opt_group)
CONF.register_opts(WATCHER_GOALS_OPTS, goals_opt_group)


class DefaultStrategySelector(base.BaseSelector):

    def __init__(self):
        super(DefaultStrategySelector, self).__init__()
        self.strategy_loader = default.DefaultStrategyLoader()

    def define_from_goal(self, goal_name, osc=None):
        """:param osc: an OpenStackClients instance"""
        strategy_to_load = None
        try:
            strategy_to_load = CONF.watcher_goals.goals[goal_name]
            return self.strategy_loader.load(strategy_to_load, osc=osc)
        except KeyError as exc:
            LOG.exception(exc)
            raise exception.WatcherException(
                _("Incorrect mapping: could not find "
                  "associated strategy for '%s'") % goal_name
            )
