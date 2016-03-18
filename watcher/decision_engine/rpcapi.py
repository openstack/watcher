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

from watcher.common import exception
from watcher.common.messaging import notification_handler
from watcher.common import service
from watcher.common import utils
from watcher.decision_engine import manager


CONF = cfg.CONF

CONF.register_group(manager.decision_engine_opt_group)
CONF.register_opts(manager.WATCHER_DECISION_ENGINE_OPTS,
                   manager.decision_engine_opt_group)


class DecisionEngineAPI(service.Service):

    def __init__(self):
        super(DecisionEngineAPI, self).__init__(DecisionEngineAPIManager)

    def trigger_audit(self, context, audit_uuid=None):
        if not utils.is_uuid_like(audit_uuid):
            raise exception.InvalidUuidOrName(name=audit_uuid)

        return self.conductor_client.call(
            context.to_dict(), 'trigger_audit', audit_uuid=audit_uuid)


class DecisionEngineAPIManager(object):

    API_VERSION = '1.0'

    conductor_endpoints = []
    status_endpoints = [notification_handler.NotificationHandler]

    def __init__(self):
        self.publisher_id = CONF.watcher_decision_engine.publisher_id
        self.conductor_topic = CONF.watcher_decision_engine.conductor_topic
        self.status_topic = CONF.watcher_decision_engine.status_topic
        self.api_version = self.API_VERSION
