# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
# Copyright (c) 2016 Intel Corp
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

from watcher.common import exception
from watcher.common import service
from watcher.common import service_manager
from watcher.common import utils

from watcher import conf

CONF = conf.CONF


class DecisionEngineAPI(service.Service):

    def __init__(self):
        super(DecisionEngineAPI, self).__init__(DecisionEngineAPIManager)

    def trigger_audit(self, context, audit_uuid=None):
        if not utils.is_uuid_like(audit_uuid):
            raise exception.InvalidUuidOrName(name=audit_uuid)

        self.conductor_client.cast(
            context, 'trigger_audit', audit_uuid=audit_uuid)

    def get_strategy_info(self, context, strategy_name):
        return self.conductor_client.call(
            context, 'get_strategy_info', strategy_name=strategy_name)

    def get_data_model_info(self, context, data_model_type, audit):
        return self.conductor_client.call(
            context, 'get_data_model_info',
            data_model_type=data_model_type, audit=audit)


class DecisionEngineAPIManager(service_manager.ServiceManager):

    @property
    def service_name(self):
        return None

    @property
    def api_version(self):
        return '1.0'

    @property
    def publisher_id(self):
        return CONF.watcher_decision_engine.publisher_id

    @property
    def conductor_topic(self):
        return CONF.watcher_decision_engine.conductor_topic

    @property
    def notification_topics(self):
        return []

    @property
    def conductor_endpoints(self):
        return []

    @property
    def notification_endpoints(self):
        return []
