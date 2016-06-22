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

from oslo_config import cfg
from oslo_log import log

from watcher.decision_engine.loading import default as loader


LOG = log.getLogger(__name__)
CONF = cfg.CONF

default_planner = 'default'

WATCHER_PLANNER_OPTS = {
    cfg.StrOpt('planner',
               default=default_planner,
               required=True,
               help='The selected planner used to schedule the actions')
}
planner_opt_group = cfg.OptGroup(name='watcher_planner',
                                 title='Defines the parameters of '
                                       'the planner')
CONF.register_group(planner_opt_group)
CONF.register_opts(WATCHER_PLANNER_OPTS, planner_opt_group)


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
