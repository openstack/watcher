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
from watcher import objects

LOG = log.getLogger(__name__)


class DefaultActionPlanHandler(base.BaseActionPlanHandler):
    def __init__(self, context, service, action_plan_uuid):
        super(DefaultActionPlanHandler, self).__init__()
        self.ctx = context
        self.service = service
        self.action_plan_uuid = action_plan_uuid

    def update_action_plan(self, uuid, state):
        action_plan = objects.ActionPlan.get_by_uuid(self.ctx, uuid)
        action_plan.state = state
        action_plan.save()

    def execute(self):
        try:
            self.update_action_plan(self.action_plan_uuid,
                                    objects.action_plan.State.ONGOING)
            applier = default.DefaultApplier(self.ctx, self.service)
            applier.execute(self.action_plan_uuid)
            state = objects.action_plan.State.SUCCEEDED
        except Exception as e:
            LOG.exception(e)
            state = objects.action_plan.State.FAILED
        finally:
            self.update_action_plan(self.action_plan_uuid, state)
