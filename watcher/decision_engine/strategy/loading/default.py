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

from watcher.decision_engine.strategy.loading.base import BaseStrategyLoader


LOG = log.getLogger(__name__)


class DefaultStrategyLoader(BaseStrategyLoader):

    def load_available_strategies(self):
        extension_manager = ExtensionManager(
            namespace='watcher_strategies',
            invoke_on_load=False,
        )
        return {ext.name: ext.plugin for ext in extension_manager.extensions}
