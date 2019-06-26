# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel Corp
#
# Authors: Prudhvi Rao Shedimbi <prudhvi.rao.shedimbi@intel.com>
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

from oslo_config import cfg

watcher_planner = cfg.OptGroup(name='watcher_planner',
                               title='Defines the parameters of '
                                     'the planner')

default_planner = 'weight'

WATCHER_PLANNER_OPTS = {
    cfg.StrOpt('planner',
               default=default_planner,
               required=True,
               help='The selected planner used to schedule the actions')
}


def register_opts(conf):
    conf.register_group(watcher_planner)
    conf.register_opts(WATCHER_PLANNER_OPTS, group=watcher_planner)


def list_opts():
    return [(watcher_planner, WATCHER_PLANNER_OPTS)]
