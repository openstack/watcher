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

from watcher.common import exception
from watcher.common.messaging import messaging_core
from watcher.common.messaging import notification_handler
from watcher.common import utils
from watcher.decision_engine.manager import decision_engine_opt_group
from watcher.decision_engine.manager import WATCHER_DECISION_ENGINE_OPTS


LOG = log.getLogger(__name__)
CONF = cfg.CONF

CONF.register_group(decision_engine_opt_group)
CONF.register_opts(WATCHER_DECISION_ENGINE_OPTS, decision_engine_opt_group)


class DecisionEngineAPI(messaging_core.MessagingCore):

    def __init__(self):
        super(DecisionEngineAPI, self).__init__(
            CONF.watcher_decision_engine.publisher_id,
            CONF.watcher_decision_engine.conductor_topic,
            CONF.watcher_decision_engine.status_topic,
            api_version=self.API_VERSION,
        )
        self.handler = notification_handler.NotificationHandler(
            self.publisher_id)
        self.status_topic_handler.add_endpoint(self.handler)

    def trigger_audit(self, context, audit_uuid=None):
        if not utils.is_uuid_like(audit_uuid):
            raise exception.InvalidUuidOrName(name=audit_uuid)

        return self.conductor_client.call(
            context.to_dict(), 'trigger_audit', audit_uuid=audit_uuid)
