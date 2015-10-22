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
from watcher.decision_engine.api.strategy.selector import Selector
from watcher.decision_engine.framework.strategy.strategy_loader import \
    StrategyLoader
from watcher.objects.audit_template import Goal
from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF

goals = {
    'SERVERS_CONSOLIDATION': 'basic',
    'MINIMIZE_ENERGY_CONSUMPTION': 'basic',
    'BALANCE_LOAD': 'basic',
    'MINIMIZE_LICENSING_COST': 'basic',
    'PREPARE_PLANNED_OPERATION': 'basic'
}
WATCHER_GOALS_OPTS = [
    cfg.DictOpt('goals',
                default=goals, help='Goals used for the optimization ')
]
goals_opt_group = cfg.OptGroup(name='watcher_goals',
                               title='Goals available for the optimization')
CONF.register_group(goals_opt_group)
CONF.register_opts(WATCHER_GOALS_OPTS, goals_opt_group)


class StrategySelector(Selector):

    def __init__(self):
        self.strategy_loader = StrategyLoader()

    def define_from_goal(self, goal_name):
        if goal_name is None:
            goal_name = Goal.SERVERS_CONSOLIDATION

        strategy_to_load = CONF.watcher_goals.goals[goal_name]
        return self.strategy_loader.load(strategy_to_load)
