# -*- encoding: utf-8 -*-
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

from oslo_log import log

from watcher.common import exception
from watcher.common import utils
from watcher.decision_engine.model import element
from watcher.decision_engine.planner import base
from watcher import objects

LOG = log.getLogger(__name__)


class NodeResourceConsolidationPlanner(base.BasePlanner):
    """Node Resource Consolidation planner implementation

    This implementation preserves the original order of actions in the
    solution and try to parallelize actions which have the same action type.

    *Limitations*

    - This is a proof of concept that is not meant to be used in production
    """

    def create_action(self,
                      action_plan_id,
                      action_type,
                      input_parameters=None):
        uuid = utils.generate_uuid()
        action = {
            'uuid': uuid,
            'action_plan_id': int(action_plan_id),
            'action_type': action_type,
            'input_parameters': input_parameters,
            'state': objects.action.State.PENDING,
            'parents': None
        }

        return action

    def schedule(self, context, audit_id, solution):
        LOG.debug('Creating an action plan for the audit uuid: %s', audit_id)
        action_plan = self._create_action_plan(context, audit_id, solution)

        actions = list(solution.actions)
        if len(actions) == 0:
            LOG.warning("The action plan is empty")
            action_plan.state = objects.action_plan.State.SUCCEEDED
            action_plan.save()
            return action_plan

        node_disabled_actions = []
        node_enabled_actions = []
        node_migrate_actions = {}
        for action in actions:
            action_type = action.get('action_type')
            parameters = action.get('input_parameters')
            json_action = self.create_action(
                action_plan_id=action_plan.id,
                action_type=action_type,
                input_parameters=parameters)
            # classing actions
            if action_type == 'change_nova_service_state':
                if parameters.get('state') == (
                        element.ServiceState.DISABLED.value):
                    node_disabled_actions.append(json_action)
                else:
                    node_enabled_actions.append(json_action)
            elif action_type == 'migrate':
                source_node = parameters.get('source_node')
                if source_node in node_migrate_actions:
                    node_migrate_actions[source_node].append(json_action)
                else:
                    node_migrate_actions[source_node] = [json_action]
            else:
                raise exception.UnsupportedActionType(
                    action_type=action.get("action_type"))

        # creating actions
        mig_parents = []
        for action in node_disabled_actions:
            mig_parents.append(action['uuid'])
            self._create_action(context, action)

        enabled_parents = []
        for actions in node_migrate_actions.values():
            enabled_parents.append(actions[-1].get('uuid'))
            pre_action_uuid = []
            for action in actions:
                action['parents'] = mig_parents + pre_action_uuid
                pre_action_uuid = [action['uuid']]
                self._create_action(context, action)

        for action in node_enabled_actions:
            action['parents'] = enabled_parents
            self._create_action(context, action)

        self._create_efficacy_indicators(
            context, action_plan.id, solution.efficacy_indicators)

        return action_plan

    def _create_action_plan(self, context, audit_id, solution):
        strategy = objects.Strategy.get_by_name(
            context, solution.strategy.name)

        action_plan_dict = {
            'uuid': utils.generate_uuid(),
            'audit_id': audit_id,
            'strategy_id': strategy.id,
            'state': objects.action_plan.State.RECOMMENDED,
            'global_efficacy': solution.global_efficacy,
        }

        new_action_plan = objects.ActionPlan(context, **action_plan_dict)
        new_action_plan.create()

        return new_action_plan

    def _create_efficacy_indicators(self, context, action_plan_id, indicators):
        efficacy_indicators = []
        for indicator in indicators:
            efficacy_indicator_dict = {
                'uuid': utils.generate_uuid(),
                'name': indicator.name,
                'description': indicator.description,
                'unit': indicator.unit,
                'value': indicator.value,
                'action_plan_id': action_plan_id,
            }
            new_efficacy_indicator = objects.EfficacyIndicator(
                context, **efficacy_indicator_dict)
            new_efficacy_indicator.create()

            efficacy_indicators.append(new_efficacy_indicator)
        return efficacy_indicators

    def _create_action(self, context, _action):
        try:
            LOG.debug("Creating the %s in the Watcher database",
                      _action.get("action_type"))

            new_action = objects.Action(context, **_action)
            new_action.create()

            return new_action
        except Exception as exc:
            LOG.exception(exc)
            raise
