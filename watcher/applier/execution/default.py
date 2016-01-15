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

from watcher._i18n import _LE
from watcher.applier.execution import base
from watcher.applier.execution import deploy_phase
from watcher.objects import action_plan

LOG = log.getLogger(__name__)


class DefaultActionPlanExecutor(base.BaseActionPlanExecutor):
    def __init__(self, manager_applier, context):
        super(DefaultActionPlanExecutor, self).__init__(manager_applier,
                                                        context)
        self.deploy = deploy_phase.DeployPhase(self)

    def execute(self, actions):
        for action in actions:
            try:
                self.notify(action, action_plan.Status.ONGOING)
                loaded_action = self.action_factory.make_action(action)
                result = self.deploy.execute_primitive(loaded_action)
                if result is False:
                    self.notify(action, action_plan.Status.FAILED)
                    self.deploy.rollback()
                    return False
                else:
                    self.deploy.populate(loaded_action)
                    self.notify(action, action_plan.Status.SUCCEEDED)
            except Exception as e:
                LOG.expection(e)
                LOG.debug('The ActionPlanExecutor failed to execute the action'
                          ' %s ', action)

                LOG.error(_LE("Trigger a rollback"))
                self.notify(action, action_plan.Status.FAILED)
                self.deploy.rollback()
                return False
        return True
