# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#
from oslo_config import cfg
from stevedore import driver
from watcher.decision_engine.strategies.basic_consolidation import \
    BasicConsolidation
from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF

strategies = {
    'basic': 'watcher.decision_engine.strategies.'
             'basic_consolidation::BasicConsolidation'
}
WATCHER_STRATEGY_OPTS = [
    cfg.DictOpt('strategies',
                default=strategies,
                help='Strategies used for the optimization ')
]
strategies_opt_group = cfg.OptGroup(
    name='watcher_strategies',
    title='Defines strategies available for the optimization')
CONF.register_group(strategies_opt_group)
CONF.register_opts(WATCHER_STRATEGY_OPTS, strategies_opt_group)


class StrategyLoader(object):

    def __init__(self):
        '''Stevedor loader

        :return:
        '''

        self.strategies = {
            None: BasicConsolidation("basic", "Basic offline consolidation"),
            "basic": BasicConsolidation(
                "basic",
                "Basic offline consolidation")
        }

    def load_driver(self, algo):
        _algo = driver.DriverManager(
            namespace='watcher_strategies',
            name=algo,
            invoke_on_load=True,
        )
        return _algo

    def load(self, model):
        return self.strategies[model]
