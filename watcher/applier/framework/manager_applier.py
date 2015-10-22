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
from concurrent.futures import ThreadPoolExecutor

from oslo_config import cfg

from watcher.applier.framework.messaging.trigger_action_plan import \
    TriggerActionPlan
from watcher.common.messaging.messaging_core import MessagingCore
from watcher.common.messaging.notification_handler import NotificationHandler
from watcher.decision_engine.framework.messaging.events import Events
from watcher.openstack.common import log

CONF = cfg.CONF

LOG = log.getLogger(__name__)

# Register options
APPLIER_MANAGER_OPTS = [
    cfg.IntOpt('applier_worker', default='1', help='The number of worker'),
    cfg.StrOpt('topic_control',
               default='watcher.applier.control',
               help='The topic name used for'
                    'control events, this topic '
                    'used for rpc call '),
    cfg.StrOpt('topic_status',
               default='watcher.applier.status',
               help='The topic name used for '
                    'status events, this topic '
                    'is used so as to notify'
                    'the others components '
                    'of the system'),
    cfg.StrOpt('publisher_id',
               default='watcher.applier.api',
               help='The identifier used by watcher '
                    'module on the message broker')
]
CONF = cfg.CONF
opt_group = cfg.OptGroup(name='watcher_applier',
                         title='Options for the Applier messaging'
                               'core')
CONF.register_group(opt_group)
CONF.register_opts(APPLIER_MANAGER_OPTS, opt_group)

CONF.import_opt('admin_user', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_tenant_name', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_password', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')


class ApplierManager(MessagingCore):
    API_VERSION = '1.0'
    # todo(jed) need workflow

    def __init__(self):
        MessagingCore.__init__(self, CONF.watcher_applier.publisher_id,
                               CONF.watcher_applier.topic_control,
                               CONF.watcher_applier.topic_status)
        # shared executor of the workflow
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.handler = NotificationHandler(self.publisher_id)
        self.handler.register_observer(self)
        self.add_event_listener(Events.ALL, self.event_receive)
        # trigger action_plan
        self.topic_control.add_endpoint(TriggerActionPlan(self))

    def join(self):
        self.topic_control.join()
        self.topic_status.join()

    def event_receive(self, event):
        try:
            request_id = event.get_request_id()
            event_type = event.get_type()
            data = event.get_data()
            LOG.debug("request id => %s" % request_id)
            LOG.debug("type_event => %s" % str(event_type))
            LOG.debug("data       => %s" % str(data))
        except Exception as e:
            LOG.error("evt %s" % e.message)
            raise e
