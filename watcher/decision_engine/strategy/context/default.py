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
from watcher.common import utils
from watcher.decision_engine.strategy.context import base
from watcher.decision_engine.strategy.selection import default

from watcher import objects

LOG = log.getLogger(__name__)


class DefaultStrategyContext(base.StrategyContext):
    def __init__(self):
        super(DefaultStrategyContext, self).__init__()
        LOG.debug("Initializing Strategy Context")

    @staticmethod
    def select_strategy(audit, request_context):
        osc = clients.OpenStackClients()
        # todo(jed) retrieve in audit parameters (threshold,...)
        # todo(jed) create ActionPlan

        goal = objects.Goal.get_by_id(request_context, audit.goal_id)

        # NOTE(jed56) In the audit object, the 'strategy_id' attribute
        # is optional. If the admin wants to force the trigger of a Strategy
        # it could specify the Strategy uuid in the Audit.
        strategy_name = None
        if audit.strategy_id:
            strategy = objects.Strategy.get_by_id(
                request_context, audit.strategy_id)
            strategy_name = strategy.name

        strategy_selector = default.DefaultStrategySelector(
            goal_name=goal.name,
            strategy_name=strategy_name,
            osc=osc)
        return strategy_selector.select()

    def do_execute_strategy(self, audit, request_context):
        selected_strategy = self.select_strategy(audit, request_context)
        selected_strategy.audit_scope = audit.scope

        schema = selected_strategy.get_schema()
        if not audit.parameters and schema:
            # Default value feedback if no predefined strategy
            utils.StrictDefaultValidatingDraft4Validator(schema).validate(
                audit.parameters)

        selected_strategy.input_parameters.update({
            name: value for name, value in audit.parameters.items()
        })

        return selected_strategy.execute(audit=audit)
