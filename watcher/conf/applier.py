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

watcher_applier = cfg.OptGroup(name='watcher_applier',
                               title='Options for the Applier messaging '
                               'core')

APPLIER_MANAGER_OPTS = [
    cfg.IntOpt('workers',
               default=1,
               min=1,
               required=True,
               help='Number of workers for applier, default value is 1.'),
    cfg.StrOpt('conductor_topic',
               default='watcher.applier.control',
               help='The topic name used for '
                    'control events, this topic '
                    'used for rpc call '),
    cfg.StrOpt('publisher_id',
               default='watcher.applier.api',
               help='The identifier used by watcher '
                    'module on the message broker'),
    cfg.StrOpt('workflow_engine',
               default='taskflow',
               required=True,
               help='Select the engine to use to execute the workflow'),
]


def register_opts(conf):
    conf.register_group(watcher_applier)
    conf.register_opts(APPLIER_MANAGER_OPTS, group=watcher_applier)


def list_opts():
    return [(watcher_applier, APPLIER_MANAGER_OPTS)]
