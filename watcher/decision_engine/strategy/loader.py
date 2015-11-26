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

from __future__ import unicode_literals

from oslo_log import log
from stevedore import ExtensionManager
from watcher.decision_engine.strategy.basic_consolidation import \
    BasicConsolidation

LOG = log.getLogger(__name__)


class StrategyLoader(object):

    default_strategy_cls = BasicConsolidation

    def load_strategies(self):
        extension_manager = ExtensionManager(
            namespace='watcher_strategies',
            invoke_on_load=True,
        )
        return {ext.name: ext.plugin for ext in extension_manager.extensions}

    def load(self, model):
        strategy = None
        try:
            available_strategies = self.load_strategies()
            strategy_cls = available_strategies.get(
                model, self.default_strategy_cls
            )
            strategy = strategy_cls()
        except Exception as exc:
            LOG.exception(exc)

        return strategy
