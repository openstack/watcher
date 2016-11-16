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

from watcher.applier.messaging import trigger
from watcher.common import service_manager

CONF = cfg.CONF


# Register options
APPLIER_MANAGER_OPTS = [
    cfg.IntOpt('workers',
               default='1',
               min=1,
               required=True,
               help='Number of workers for applier, default value is 1.'),
    cfg.StrOpt('conductor_topic',
               default='watcher.applier.control',
               help='The topic name used for'
                    'control events, this topic '
                    'used for rpc call '),
    cfg.StrOpt('publisher_id',
               default='watcher.applier.api',
               help='The identifier used by watcher '
                    'module on the message broker'),
    cfg.StrOpt('workflow_engine',
               default='taskflow',
               required=True,
               help='Select the engine to use to execute the workflow')
]

opt_group = cfg.OptGroup(name='watcher_applier',
                         title='Options for the Applier messaging'
                               'core')
CONF.register_group(opt_group)
CONF.register_opts(APPLIER_MANAGER_OPTS, opt_group)


class ApplierManager(service_manager.ServiceManager):

    @property
    def service_name(self):
        return 'watcher-applier'

    @property
    def api_version(self):
        return '1.0'

    @property
    def publisher_id(self):
        return CONF.watcher_applier.publisher_id

    @property
    def conductor_topic(self):
        return CONF.watcher_applier.conductor_topic

    @property
    def notification_topics(self):
        return []

    @property
    def conductor_endpoints(self):
        return [trigger.TriggerActionPlan]

    @property
    def notification_endpoints(self):
        return []
