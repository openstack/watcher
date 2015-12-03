# -*- encoding: utf-8 -*-
# Copyright 2014
# The Cloudscaling Group, Inc.
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

import watcher.api.app
from watcher.applier import manager_applier
from watcher.decision_engine import manager
from watcher.decision_engine.strategy.selector import default \
    as strategy_selector


def list_opts():
    return [
        ('api', watcher.api.app.API_SERVICE_OPTS),
        ('watcher_goals', strategy_selector.WATCHER_GOALS_OPTS),
        ('watcher_decision_engine',
         manager.WATCHER_DECISION_ENGINE_OPTS),
        ('watcher_applier',
         manager_applier.APPLIER_MANAGER_OPTS)
    ]
