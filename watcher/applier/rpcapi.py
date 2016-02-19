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
import oslo_messaging as om

from watcher.applier.manager import APPLIER_MANAGER_OPTS
from watcher.applier.manager import opt_group
from watcher.common import exception
from watcher.common.messaging import messaging_core
from watcher.common.messaging import notification_handler as notification
from watcher.common import utils


LOG = log.getLogger(__name__)
CONF = cfg.CONF
CONF.register_group(opt_group)
CONF.register_opts(APPLIER_MANAGER_OPTS, opt_group)


class ApplierAPI(messaging_core.MessagingCore):

    def __init__(self):
        super(ApplierAPI, self).__init__(
            CONF.watcher_applier.publisher_id,
            CONF.watcher_applier.conductor_topic,
            CONF.watcher_applier.status_topic,
            api_version=self.API_VERSION,
        )
        self.handler = notification.NotificationHandler(self.publisher_id)
        self.handler.register_observer(self)
        self.status_topic_handler.add_endpoint(self.handler)
        transport = om.get_transport(CONF)

        target = om.Target(
            topic=CONF.watcher_applier.conductor_topic,
            version=self.API_VERSION,
        )

        self.client = om.RPCClient(transport, target,
                                   serializer=self.serializer)

    def launch_action_plan(self, context, action_plan_uuid=None):
        if not utils.is_uuid_like(action_plan_uuid):
            raise exception.InvalidUuidOrName(name=action_plan_uuid)

        return self.client.call(
            context.to_dict(), 'launch_action_plan',
            action_plan_uuid=action_plan_uuid)
