# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from watcher.common.messaging.events.event import Event
from watcher.decision_engine.api.messaging.decision_engine_command import \
    DecisionEngineCommand
from watcher.decision_engine.framework.default_planner import DefaultPlanner
from watcher.decision_engine.framework.messaging.events import Events
from watcher.decision_engine.framework.strategy.StrategyManagerImpl import \
    StrategyContextImpl
from watcher.objects.audit import Audit
from watcher.objects.audit import AuditStatus
from watcher.objects.audit_template import AuditTemplate
from watcher.openstack.common import log

LOG = log.getLogger(__name__)


class TriggerAuditCommand(DecisionEngineCommand):
    def __init__(self, messaging, statedb, ressourcedb):
        self.messaging = messaging
        self.statedb = statedb
        self.ressourcedb = ressourcedb
        self.strategy_context = StrategyContextImpl()

    def notify(self, audit_uuid, event_type, status):
        event = Event()
        event.set_type(event_type)
        event.set_data({})
        payload = {'audit_uuid': audit_uuid,
                   'audit_status': status}
        self.messaging.topic_status.publish_event(event.get_type().name,
                                                  payload)

    def update_audit(self, request_context, audit_uuid, state):
        LOG.debug("update audit " + str(state))
        audit = Audit.get_by_uuid(request_context, audit_uuid)
        audit.state = state
        audit.save()
        self.notify(audit_uuid, Events.TRIGGER_AUDIT, state)
        return audit

    def execute(self, audit_uuid, request_context):
        try:
            LOG.debug("Execute TriggerAuditCommand ")

            # 1 - change status to ONGOING
            audit = self.update_audit(request_context, audit_uuid,
                                      AuditStatus.ONGOING)

            # 3 - Retrieve metrics
            cluster = self.statedb.get_latest_state_cluster()

            # 4 - Select appropriate strategy
            audit_template = AuditTemplate.get_by_id(request_context,
                                                     audit.audit_template_id)

            self.strategy_context.set_goal(audit_template.goal)
            self.strategy_context.set_metrics_resource_collector(
                self.ressourcedb)

            # 5 - compute change requests
            solution = self.strategy_context.execute_strategy(cluster)

            # 6 - create an action plan
            planner = DefaultPlanner()
            planner.schedule(request_context, audit.id, solution)

            # 7 - change status to SUCCESS and notify
            self.update_audit(request_context, audit_uuid, AuditStatus.SUCCESS)
        except Exception as e:
            self.update_audit(request_context, audit_uuid, AuditStatus.FAILED)
            LOG.error(" " + unicode(e))
