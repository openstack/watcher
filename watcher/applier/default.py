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
from oslo_config import cfg
from oslo_log import log

from watcher.applier import base
from watcher.applier.loading import default
from watcher import objects

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class DefaultApplier(base.BaseApplier):
    def __init__(self, context, applier_manager):
        super(DefaultApplier, self).__init__()
        self._applier_manager = applier_manager
        self._loader = default.DefaultWorkFlowEngineLoader()
        self._engine = None
        self._context = context

    @property
    def context(self):
        return self._context

    @property
    def applier_manager(self):
        return self._applier_manager

    @property
    def engine(self):
        if self._engine is None:
            selected_workflow_engine = CONF.watcher_applier.workflow_engine
            LOG.debug("Loading workflow engine %s ", selected_workflow_engine)
            self._engine = self._loader.load(
                name=selected_workflow_engine,
                context=self.context,
                applier_manager=self.applier_manager)
        return self._engine

    def execute(self, action_plan_uuid):
        LOG.debug("Executing action plan %s ", action_plan_uuid)

        filters = {'action_plan_uuid': action_plan_uuid}
        actions = objects.Action.list(self.context, filters=filters,
                                      eager=True)
        return self.engine.execute(actions)
