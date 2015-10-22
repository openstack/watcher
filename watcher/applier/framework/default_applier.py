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
from watcher.applier.api.applier import Applier
from watcher.applier.framework.command_executor import CommandExecutor
from watcher.objects import Action
from watcher.objects import ActionPlan


class DefaultApplier(Applier):
    def __init__(self, manager_applier, context):
        self.manager_applier = manager_applier
        self.context = context
        self.executor = CommandExecutor(manager_applier, context)

    def execute(self, action_plan_uuid):
        action_plan = ActionPlan.get_by_uuid(self.context, action_plan_uuid)
        # todo(jed) remove direct access to dbapi need filter in object
        actions = Action.dbapi.get_action_list(self.context,
                                               filters={
                                                   'action_plan_id':
                                                       action_plan.id})
        return self.executor.execute(actions)
