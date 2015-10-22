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
import oslo_messaging as om


from watcher.applier.framework.manager_applier import APPLIER_MANAGER_OPTS
from watcher.applier.framework.manager_applier import opt_group
from watcher.common import exception
from watcher.common import utils


from watcher.common.messaging.messaging_core import MessagingCore
from watcher.common.messaging.notification_handler import NotificationHandler
from watcher.common.messaging.utils.transport_url_builder import \
    TransportUrlBuilder
from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF
CONF.register_group(opt_group)
CONF.register_opts(APPLIER_MANAGER_OPTS, opt_group)


class ApplierAPI(MessagingCore):
    MessagingCore.API_VERSION = '1.0'

    def __init__(self):
        MessagingCore.__init__(self, CONF.watcher_applier.publisher_id,
                               CONF.watcher_applier.topic_control,
                               CONF.watcher_applier.topic_status)
        self.handler = NotificationHandler(self.publisher_id)
        self.handler.register_observer(self)
        self.topic_status.add_endpoint(self.handler)
        transport = om.get_transport(CONF, TransportUrlBuilder().url)
        target = om.Target(
            topic=CONF.watcher_applier.topic_control,
            version=MessagingCore.API_VERSION)

        self.client = om.RPCClient(transport, target,
                                   serializer=self.serializer)

    def launch_action_plan(self, context, action_plan_uuid=None):
        if not utils.is_uuid_like(action_plan_uuid):
            raise exception.InvalidUuidOrName(name=action_plan_uuid)

        return self.client.call(
            context.to_dict(), 'launch_action_plan',
            action_plan_uuid=action_plan_uuid)

    def event_receive(self, event):
        try:
            pass
        except Exception as e:
            LOG.error("evt %s" % e.message)
            raise e
