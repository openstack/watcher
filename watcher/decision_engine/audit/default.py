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
from oslo_log import log

from watcher.common.messaging.events.event import Event
from watcher.decision_engine.audit.base import \
    BaseAuditHandler
from watcher.decision_engine.messaging.events import Events
from watcher.decision_engine.planner.manager import PlannerManager
from watcher.decision_engine.strategy.context.default import \
    DefaultStrategyContext
from watcher.objects.audit import Audit
from watcher.objects.audit import AuditStatus


LOG = log.getLogger(__name__)


class DefaultAuditHandler(BaseAuditHandler):
    def __init__(self, messaging):
        super(DefaultAuditHandler, self).__init__()
        self._messaging = messaging
        self._strategy_context = DefaultStrategyContext()
        self._planner_manager = PlannerManager()
        self._planner = None

    @property
    def planner(self):
        if self._planner is None:
            self._planner = self._planner_manager.load()
        return self._planner

    @property
    def messaging(self):
        return self._messaging

    @property
    def strategy_context(self):
        return self._strategy_context

    def notify(self, audit_uuid, event_type, status):
        event = Event()
        event.type = event_type
        event.data = {}
        payload = {'audit_uuid': audit_uuid,
                   'audit_status': status}
        self.messaging.topic_status.publish_event(event.type.name,
                                                  payload)

    def update_audit_state(self, request_context, audit_uuid, state):
        LOG.debug("Update audit state:{0} ".format(state))
        audit = Audit.get_by_uuid(request_context, audit_uuid)
        audit.state = state
        audit.save()
        self.notify(audit_uuid, Events.TRIGGER_AUDIT, state)
        return audit

    def execute(self, audit_uuid, request_context):
        try:
            LOG.debug("Trigger audit %s" % audit_uuid)

            # change state of the audit to ONGOING
            audit = self.update_audit_state(request_context, audit_uuid,
                                            AuditStatus.ONGOING)

            # execute the strategy
            solution = self.strategy_context.execute_strategy(audit_uuid,
                                                              request_context)

            self.planner.schedule(request_context, audit.id, solution)

            # change state of the audit to SUCCEEDED
            self.update_audit_state(request_context, audit_uuid,
                                    AuditStatus.SUCCEEDED)
        except Exception as e:
            LOG.exception(e)
            self.update_audit_state(request_context, audit_uuid,
                                    AuditStatus.FAILED)
