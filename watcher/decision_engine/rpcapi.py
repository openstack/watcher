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

from watcher.common import exception
from watcher.common.messaging.messaging_core import MessagingCore
from watcher.common import utils
from watcher.decision_engine.manager import decision_engine_opt_group
from watcher.decision_engine.manager import WATCHER_DECISION_ENGINE_OPTS


LOG = log.getLogger(__name__)
CONF = cfg.CONF

CONF.register_group(decision_engine_opt_group)
CONF.register_opts(WATCHER_DECISION_ENGINE_OPTS, decision_engine_opt_group)


class DecisionEngineAPI(MessagingCore):

    def __init__(self):
        super(DecisionEngineAPI, self).__init__(
            CONF.watcher_decision_engine.publisher_id,
            CONF.watcher_decision_engine.topic_control,
            CONF.watcher_decision_engine.topic_status,
            api_version=self.API_VERSION,
        )

        transport = om.get_transport(CONF)
        target = om.Target(
            topic=CONF.watcher_decision_engine.topic_control,
            version=self.API_VERSION,
        )
        self.client = om.RPCClient(transport, target,
                                   serializer=self.serializer)

    def trigger_audit(self, context, audit_uuid=None):
        if not utils.is_uuid_like(audit_uuid):
            raise exception.InvalidUuidOrName(name=audit_uuid)

        return self.client.call(
            context.to_dict(), 'trigger_audit', audit_uuid=audit_uuid)
