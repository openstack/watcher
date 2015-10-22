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

from watcher.applier.framework.messaging.launch_action_plan import \
    LaunchActionPlanCommand
from watcher.openstack.common import log

LOG = log.getLogger(__name__)


class TriggerActionPlan(object):
    def __init__(self, manager_applier):
        self.manager_applier = manager_applier

    def do_launch_action_plan(self, context, action_plan_uuid):
        try:
            cmd = LaunchActionPlanCommand(context,
                                          self.manager_applier,
                                          action_plan_uuid)
            cmd.execute()
        except Exception as e:
            LOG.error("do_launch_action_plan " + unicode(e))

    def launch_action_plan(self, context, action_plan_uuid):
        LOG.debug("Trigger ActionPlan %s" % action_plan_uuid)
        # submit
        self.manager_applier.executor.submit(self.do_launch_action_plan,
                                             context,
                                             action_plan_uuid)
        return action_plan_uuid
