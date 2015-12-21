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
import abc
from oslo_log import log
import six

from watcher.decision_engine.strategy.strategies.dummy_strategy import \
    DummyStrategy

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseStrategyLoader(object):
    default_strategy_cls = DummyStrategy

    @abc.abstractmethod
    def load_available_strategies(self):
        raise NotImplementedError()

    def load(self, strategy_to_load=None):
        strategy_selected = None
        try:
            available_strategies = self.load_available_strategies()
            LOG.debug("Available strategies: %s ", available_strategies)
            strategy_cls = available_strategies.get(
                strategy_to_load, self.default_strategy_cls
            )
            strategy_selected = strategy_cls()
        except Exception as exc:
            LOG.exception(exc)

        return strategy_selected
