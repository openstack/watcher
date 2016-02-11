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

from oslo_log import log

from watcher._i18n import _LW
from watcher.common import utils
from watcher.decision_engine.planner import base
from watcher import objects

LOG = log.getLogger(__name__)


class DefaultPlanner(base.BasePlanner):
    """Default planner implementation

    This implementation comes with basic rules with a fixed set of action types
    that are weighted. An action having a lower weight will be scheduled before
    the other ones.
    """

    priorities = {
        'nop': 0,
        'sleep': 1,
        'change_nova_service_state': 2,
        'migrate': 3,
    }

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
            'alarm': None,
            'next': None,
        }
        return action

    def schedule(self, context, audit_id, solution):
        LOG.debug('Create an action plan for the audit uuid: %s ', audit_id)
        action_plan = self._create_action_plan(context, audit_id)

        actions = list(solution.actions)
        to_schedule = []
        for action in actions:
            json_action = self.create_action(action_plan_id=action_plan.id,
                                             action_type=action.get(
                                                 'action_type'),
                                             input_parameters=action.get(
                                                 'input_parameters'))
            to_schedule.append((self.priorities[action.get('action_type')],
                                json_action))

        # scheduling
        scheduled = sorted(to_schedule, key=lambda x: (x[0]))
        if len(scheduled) == 0:
            LOG.warning(_LW("The action plan is empty"))
            action_plan.first_action_id = None
            action_plan.save()
        else:
            # create the first action
            parent_action = self._create_action(context,
                                                scheduled[0][1],
                                                None)
            # remove first
            scheduled.pop(0)

            action_plan.first_action_id = parent_action.id
            action_plan.save()

            for s_action in scheduled:
                current_action = self._create_action(context, s_action[1],
                                                     parent_action)
                parent_action = current_action

        return action_plan

    def _create_action_plan(self, context, audit_id):
        action_plan_dict = {
            'uuid': utils.generate_uuid(),
            'audit_id': audit_id,
            'first_action_id': None,
            'state': objects.action_plan.State.RECOMMENDED
        }

        new_action_plan = objects.ActionPlan(context, **action_plan_dict)
        new_action_plan.create(context)
        new_action_plan.save()
        return new_action_plan

    def _create_action(self, context, _action, parent_action):
        try:
            LOG.debug("Creating the %s in watcher db",
                      _action.get("action_type"))

            new_action = objects.Action(context, **_action)
            new_action.create(context)
            new_action.save()

            if parent_action:
                parent_action.next = new_action.id
                parent_action.save()

            return new_action
        except Exception as exc:
            LOG.exception(exc)
            raise
