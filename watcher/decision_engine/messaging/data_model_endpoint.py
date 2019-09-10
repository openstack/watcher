# -*- encoding: utf-8 -*-
# Copyright 2019 ZTE corporation.
# All Rights Reserved.
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
from watcher.common import utils
from watcher.decision_engine.model.collector import manager
from watcher import objects


class DataModelEndpoint(object):
    def __init__(self, messaging):
        self._messaging = messaging

    def get_audit_scope(self, context, audit=None):
        scope = None
        try:
            if utils.is_uuid_like(audit) or utils.is_int_like(audit):
                audit = objects.Audit.get(
                    context, audit)
            else:
                audit = objects.Audit.get_by_name(
                    context, audit)
        except exception.AuditNotFound:
            raise exception.InvalidIdentity(identity=audit)
        if audit:
            scope = audit.scope
        else:
            scope = []
        return scope

    def get_data_model_info(self, context, data_model_type='compute',
                            audit=None):
        if audit is not None:
            scope = self.get_audit_scope(context, audit)
        else:
            scope = []
        collector_manager = manager.CollectorManager()
        collector = collector_manager.get_cluster_model_collector(
            data_model_type)
        audit_scope_handler = collector.get_audit_scope_handler(
            audit_scope=scope)
        available_data_model = audit_scope_handler.get_scoped_model(
            collector.get_latest_cluster_data_model())
        if not available_data_model:
            return {"context": []}
        return {"context": available_data_model.to_list()}
