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
import time
from watcher.decision_engine.strategies.basic_consolidation import \
    BasicConsolidation

from watcher.openstack.common import log

from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector
from watcher.tests.decision_engine.faker_metrics_collector import \
    FakerMetricsCollector


LOG = log.getLogger(__name__)

cfg.CONF.debug = True
log.setup('metering-controller')

metrics = FakerMetricsCollector()
current_state_cluster = FakerStateCollector()

sercon = BasicConsolidation("basic", "Basic offline consolidation")
sercon.set_metrics_resource_collector(metrics)

start_time = time.clock()
solution = sercon.execute(current_state_cluster.generate_scenario_1())
print(time.clock() - start_time, "seconds")
print(solution)
# planner = DefaultPlanner()
# planner.schedule(solution)
