# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

from watcher.decision_engine.loading import default as loader

from watcher import conf

LOG = log.getLogger(__name__)
CONF = conf.CONF


class PlannerManager(object):
    def __init__(self):
        self._loader = loader.DefaultPlannerLoader()

    @property
    def loader(self):
        return self._loader

    def load(self):
        selected_planner = CONF.watcher_planner.planner
        LOG.debug("Loading %s", selected_planner)
        return self.loader.load(name=selected_planner)
