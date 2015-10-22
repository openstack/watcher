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
from watcher.applier.api.messaging.applier_command import ApplierCommand
from watcher.applier.framework.default_applier import DefaultApplier
from watcher.applier.framework.messaging.events import Events
from watcher.common.messaging.events.event import Event
from watcher.objects.action_plan import ActionPlan
from watcher.objects.action_plan import Status

from watcher.openstack.common import log

LOG = log.getLogger(__name__)


class LaunchActionPlanCommand(ApplierCommand):
    def __init__(self, context, manager_applier, action_plan_uuid):
        self.ctx = context
        self.action_plan_uuid = action_plan_uuid
        self.manager_applier = manager_applier

    def notify(self, uuid, event_type, status):
        action_plan = ActionPlan.get_by_uuid(self.ctx, uuid)
        action_plan.state = status
        action_plan.save()
        event = Event()
        event.set_type(event_type)
        event.set_data({})
        payload = {'action_plan__uuid': uuid,
                   'action_plan_status': status}
        self.manager_applier.topic_status.publish_event(event.get_type().name,
                                                        payload)

    def execute(self):
        try:
            # update state
            self.notify(self.action_plan_uuid,
                        Events.LAUNCH_ACTION_PLAN,
                        Status.ONGOING)
            applier = DefaultApplier(self.manager_applier, self.ctx)
            result = applier.execute(self.action_plan_uuid)
        except Exception as e:
            result = False
            LOG.error("Launch Action Plan " + unicode(e))
        finally:
            if result is True:
                status = Status.SUCCESS
            else:
                status = Status.FAILED
            # update state
            self.notify(self.action_plan_uuid, Events.LAUNCH_ACTION_PLAN,
                        status)
