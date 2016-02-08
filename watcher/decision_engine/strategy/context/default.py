# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from oslo_log import log

from watcher.common import clients
from watcher.decision_engine.strategy.context import base
from watcher.decision_engine.strategy.selection import default
from watcher.metrics_engine.cluster_model_collector import manager

from watcher import objects

LOG = log.getLogger(__name__)


class DefaultStrategyContext(base.BaseStrategyContext):
    def __init__(self):
        super(DefaultStrategyContext, self).__init__()
        LOG.debug("Initializing Strategy Context")
        self._strategy_selector = default.DefaultStrategySelector()
        self._collector_manager = manager.CollectorManager()

    @property
    def collector(self):
        return self._collector_manager

    @property
    def strategy_selector(self):
        return self._strategy_selector

    def execute_strategy(self, audit_uuid, request_context):
        audit = objects.Audit.get_by_uuid(request_context, audit_uuid)

        # Retrieve the Audit Template
        audit_template = objects.\
            AuditTemplate.get_by_id(request_context, audit.audit_template_id)

        osc = clients.OpenStackClients()

        # todo(jed) retrieve in audit_template parameters (threshold,...)
        # todo(jed) create ActionPlan
        collector_manager = self.collector.get_cluster_model_collector(osc=osc)

        # todo(jed) remove call to get_latest_cluster_data_model
        cluster_data_model = collector_manager.get_latest_cluster_data_model()

        selected_strategy = self.strategy_selector.define_from_goal(
            audit_template.goal, osc=osc)

        # todo(jed) add parameters and remove cluster_data_model
        return selected_strategy.execute(cluster_data_model)
