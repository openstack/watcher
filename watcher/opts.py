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

import itertools

import watcher.api.app
from watcher.applier.framework import manager_applier
import watcher.common.messaging.messaging_core

import watcher.openstack.common.log

from watcher.decision_engine.framework import manager_decision_engine
from watcher.decision_engine.framework.strategy import strategy_loader
from watcher.decision_engine.framework.strategy import strategy_selector
from watcher.metrics_engine.framework import collector_manager
from watcher.metrics_engine.framework.datasources import influxdb_collector


def list_opts():
    return [
        ('DEFAULT', itertools.chain(
            watcher.openstack.common.log.generic_log_opts,
            watcher.openstack.common.log.log_opts,
            watcher.openstack.common.log.common_cli_opts,
            watcher.openstack.common.log.logging_cli_opts
        )),
        ('api', watcher.api.app.API_SERVICE_OPTS),
        ('watcher_messaging',
         watcher.common.messaging.messaging_core.WATCHER_MESSAGING_OPTS),
        ('watcher_strategies', strategy_loader.WATCHER_STRATEGY_OPTS),
        ('watcher_goals', strategy_selector.WATCHER_GOALS_OPTS),
        ('watcher_decision_engine',
         manager_decision_engine.WATCHER_DECISION_ENGINE_OPTS),
        ('watcher_applier',
         manager_applier.APPLIER_MANAGER_OPTS),
        ('watcher_influxdb_collector',
         influxdb_collector.WATCHER_INFLUXDB_COLLECTOR_OPTS),
        ('watcher_metrics_collector',
         collector_manager.WATCHER_METRICS_COLLECTOR_OPTS)
    ]
