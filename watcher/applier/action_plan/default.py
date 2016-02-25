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

from watcher.applier.action_plan import base
from watcher.applier import default
from watcher.applier.messaging import event_types
from watcher.common.messaging.events import event
from watcher.objects import action_plan as ap_objects

LOG = log.getLogger(__name__)


class DefaultActionPlanHandler(base.BaseActionPlanHandler):
    def __init__(self, context, applier_manager, action_plan_uuid):
        super(DefaultActionPlanHandler, self).__init__()
        self.ctx = context
        self.action_plan_uuid = action_plan_uuid
        self.applier_manager = applier_manager

    def notify(self, uuid, event_type, state):
        action_plan = ap_objects.ActionPlan.get_by_uuid(self.ctx, uuid)
        action_plan.state = state
        action_plan.save()
        ev = event.Event()
        ev.type = event_type
        ev.data = {}
        payload = {'action_plan__uuid': uuid,
                   'action_plan_state': state}
        self.applier_manager.status_topic_handler.publish_event(
            ev.type.name, payload)

    def execute(self):
        try:
            # update state
            self.notify(self.action_plan_uuid,
                        event_types.EventTypes.LAUNCH_ACTION_PLAN,
                        ap_objects.State.ONGOING)
            applier = default.DefaultApplier(self.ctx, self.applier_manager)
            applier.execute(self.action_plan_uuid)
            state = ap_objects.State.SUCCEEDED

        except Exception as e:
            LOG.exception(e)
            state = ap_objects.State.FAILED

        finally:
            # update state
            self.notify(self.action_plan_uuid,
                        event_types.EventTypes.LAUNCH_ACTION_PLAN,
                        state)
