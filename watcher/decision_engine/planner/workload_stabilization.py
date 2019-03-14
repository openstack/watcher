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

import abc

from oslo_config import cfg
from oslo_log import log

from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import utils
from watcher.decision_engine.planner import base
from watcher import objects

LOG = log.getLogger(__name__)


class WorkloadStabilizationPlanner(base.BasePlanner):
    """Workload Stabilization planner implementation

    This implementation comes with basic rules with a set of action types that
    are weighted. An action having a lower weight will be scheduled before the
    other ones. The set of action types can be specified by 'weights' in the
    ``watcher.conf``. You need to associate a different weight to all available
    actions into the configuration file, otherwise you will get an error when
    the new action will be referenced in the solution produced by a strategy.

    *Limitations*

    - This is a proof of concept that is not meant to be used in production
    """

    def __init__(self, config):
        super(WorkloadStabilizationPlanner, self).__init__(config)
        self._osc = clients.OpenStackClients()

    @property
    def osc(self):
        return self._osc

    weights_dict = {
        'turn_host_to_acpi_s3_state': 0,
        'resize': 1,
        'migrate': 2,
        'sleep': 3,
        'change_nova_service_state': 4,
        'nop': 5,
    }

    @classmethod
    def get_config_opts(cls):
        return [
            cfg.DictOpt(
                'weights',
                help="These weights are used to schedule the actions",
                default=cls.weights_dict),
        ]

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

    def load_child_class(self, child_name):
        for c in BaseActionValidator.__subclasses__():
            if child_name == c.action_name:
                return c()
        return None

    def schedule(self, context, audit_id, solution):
        LOG.debug('Creating an action plan for the audit uuid: %s', audit_id)
        weights = self.config.weights
        action_plan = self._create_action_plan(context, audit_id, solution)

        actions = list(solution.actions)
        to_schedule = []
        for action in actions:
            json_action = self.create_action(
                action_plan_id=action_plan.id,
                action_type=action.get('action_type'),
                input_parameters=action.get('input_parameters'))
            to_schedule.append((weights[action.get('action_type')],
                                json_action))

        self._create_efficacy_indicators(
            context, action_plan.id, solution.efficacy_indicators)

        # scheduling
        scheduled = sorted(to_schedule, key=lambda weight: (weight[0]),
                           reverse=True)
        if len(scheduled) == 0:
            LOG.warning("The action plan is empty")
            action_plan.state = objects.action_plan.State.SUCCEEDED
            action_plan.save()
        else:
            resource_action_map = {}
            scheduled_actions = [x[1] for x in scheduled]
            for action in scheduled_actions:
                a_type = action['action_type']
                if a_type != 'turn_host_to_acpi_s3_state':
                    plugin_action = self.load_child_class(
                        action.get("action_type"))
                    if not plugin_action:
                        raise exception.UnsupportedActionType(
                            action_type=action.get("action_type"))
                    db_action = self._create_action(context, action)
                    parents = plugin_action.validate_parents(
                        resource_action_map, action)
                    if parents:
                        db_action.parents = parents
                        db_action.save()
                # if we have an action that will make host unreachable, we need
                # to complete all actions (resize and migration type)
                # related to the host.
                # Note(alexchadin): turn_host_to_acpi_s3_state doesn't
                # actually exist. Placed code shows relations between
                # action types.
                # TODO(alexchadin): add turn_host_to_acpi_s3_state action type.
                else:
                    host_to_acpi_s3 = action['input_parameters']['resource_id']
                    host_actions = resource_action_map.get(host_to_acpi_s3)
                    action_parents = []
                    if host_actions:
                        resize_actions = [x[0] for x in host_actions
                                          if x[1] == 'resize']
                        migrate_actions = [x[0] for x in host_actions
                                           if x[1] == 'migrate']
                        resize_migration_parents = [
                            x.parents for x in
                            [objects.Action.get_by_uuid(context, resize_action)
                             for resize_action in resize_actions]]
                        # resize_migration_parents should be one level list
                        resize_migration_parents = [
                            parent for sublist in resize_migration_parents
                            for parent in sublist]
                        action_parents.extend([uuid for uuid in
                                               resize_actions])
                        action_parents.extend([uuid for uuid in
                                              migrate_actions if uuid not in
                                              resize_migration_parents])
                    db_action = self._create_action(context, action)
                    db_action.parents = action_parents
                    db_action.save()

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


class BaseActionValidator(object):
    action_name = None

    def __init__(self):
        super(BaseActionValidator, self).__init__()
        self._osc = None

    @property
    def osc(self):
        if not self._osc:
            self._osc = clients.OpenStackClients()
        return self._osc

    @abc.abstractmethod
    def validate_parents(self, resource_action_map, action):
        raise NotImplementedError()

    def _mapping(self, resource_action_map, resource_id, action_uuid,
                 action_type):
        if resource_id not in resource_action_map:
            resource_action_map[resource_id] = [(action_uuid,
                                                 action_type,)]
        else:
            resource_action_map[resource_id].append((action_uuid,
                                                     action_type,))


class MigrationActionValidator(BaseActionValidator):
    action_name = "migrate"

    def validate_parents(self, resource_action_map, action):
        instance_uuid = action['input_parameters']['resource_id']
        host_name = action['input_parameters']['source_node']
        self._mapping(resource_action_map, instance_uuid, action['uuid'],
                      'migrate')
        self._mapping(resource_action_map, host_name, action['uuid'],
                      'migrate')


class ResizeActionValidator(BaseActionValidator):
    action_name = "resize"

    def validate_parents(self, resource_action_map, action):
        nova = nova_helper.NovaHelper(osc=self.osc)
        instance_uuid = action['input_parameters']['resource_id']
        parent_actions = resource_action_map.get(instance_uuid)
        host_of_instance = nova.get_hostname(
            nova.get_instance_by_uuid(instance_uuid)[0])
        self._mapping(resource_action_map, host_of_instance, action['uuid'],
                      'resize')
        if parent_actions:
            return [x[0] for x in parent_actions]
        else:
            return []


class ChangeNovaServiceStateActionValidator(BaseActionValidator):
    action_name = "change_nova_service_state"

    def validate_parents(self, resource_action_map, action):
        host_name = action['input_parameters']['resource_id']
        self._mapping(resource_action_map, host_name, action['uuid'],
                      'change_nova_service_state')
        return []


class SleepActionValidator(BaseActionValidator):
    action_name = "sleep"

    def validate_parents(self, resource_action_map, action):
        return []


class NOPActionValidator(BaseActionValidator):
    action_name = "nop"

    def validate_parents(self, resource_action_map, action):
        return []
