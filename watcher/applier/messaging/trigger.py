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
from oslo_config import cfg
from oslo_log import log

from watcher.applier.action_plan import default
from watcher.common import executor

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class TriggerActionPlan:
    def __init__(self, applier_manager):
        self.applier_manager = applier_manager
        workers = CONF.watcher_applier.workers
        self.executor = executor.get_futurist_pool_executor(
            max_workers=workers)

    def do_launch_action_plan(self, context, action_plan_uuid):
        try:
            cmd = default.DefaultActionPlanHandler(context,
                                                   self.applier_manager,
                                                   action_plan_uuid)
            cmd.execute()
        except Exception as e:
            LOG.exception(e)

    def launch_action_plan(self, context, action_plan_uuid):
        LOG.debug("Trigger ActionPlan %s", action_plan_uuid)
        # submit
        executor.log_executor_stats(self.executor, name="action-plan-pool")
        self.executor.submit(self.do_launch_action_plan, context,
                             action_plan_uuid)
        return action_plan_uuid
