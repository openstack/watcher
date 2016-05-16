# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#          Alexander Chadin <a.chadin@servionica.ru>
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
import abc
import six

from oslo_log import log

from watcher.common.messaging.events import event as watcher_event
from watcher.decision_engine.messaging import events as de_events
from watcher.decision_engine.planner import manager as planner_manager
from watcher.decision_engine.strategy.context import default as default_context
from watcher.objects import audit as audit_objects

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseAuditHandler(object):
    @abc.abstractmethod
    def execute(self, audit_uuid, request_context):
        raise NotImplementedError()

    @abc.abstractmethod
    def pre_execute(self, audit_uuid, request_context):
        raise NotImplementedError()

    @abc.abstractmethod
    def do_execute(self, audit, request_context):
        raise NotImplementedError()

    @abc.abstractmethod
    def post_execute(self, audit, solution, request_context):
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class AuditHandler(BaseAuditHandler):
    def __init__(self, messaging):
        self._messaging = messaging
        self._strategy_context = default_context.DefaultStrategyContext()
        self._planner_manager = planner_manager.PlannerManager()
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
        event = watcher_event.Event()
        event.type = event_type
        event.data = {}
        payload = {'audit_uuid': audit_uuid,
                   'audit_status': status}
        self.messaging.status_topic_handler.publish_event(
            event.type.name, payload)

    def update_audit_state(self, request_context, audit, state):
        LOG.debug("Update audit state: %s", state)
        audit.state = state
        audit.save()
        self.notify(audit.uuid, de_events.Events.TRIGGER_AUDIT, state)

    def pre_execute(self, audit, request_context):
        LOG.debug("Trigger audit %s", audit.uuid)
        # change state of the audit to ONGOING
        self.update_audit_state(request_context, audit,
                                audit_objects.State.ONGOING)

    def post_execute(self, audit, solution, request_context):
        self.planner.schedule(request_context, audit.id, solution)

        # change state of the audit to SUCCEEDED
        self.update_audit_state(request_context, audit,
                                audit_objects.State.SUCCEEDED)

    def execute(self, audit, request_context):
        try:
            self.pre_execute(audit, request_context)
            solution = self.do_execute(audit, request_context)
            self.post_execute(audit, solution, request_context)
        except Exception as e:
            LOG.exception(e)
            self.update_audit_state(request_context, audit,
                                    audit_objects.State.FAILED)
