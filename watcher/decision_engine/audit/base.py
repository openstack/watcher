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

from oslo_config import cfg
from oslo_log import log

from watcher.applier import rpcapi
from watcher.common import exception
from watcher.common import service
from watcher.decision_engine.loading import default as loader
from watcher.decision_engine.strategy.context import default as default_context
from watcher import notifications
from watcher import objects
from watcher.objects import fields

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class BaseMetaClass(service.Singleton, abc.ABCMeta):
    pass


class BaseAuditHandler(object, metaclass=BaseMetaClass):

    @abc.abstractmethod
    def execute(self, audit, request_context):
        raise NotImplementedError()

    @abc.abstractmethod
    def pre_execute(self, audit, request_context):
        raise NotImplementedError()

    @abc.abstractmethod
    def do_execute(self, audit, request_context):
        raise NotImplementedError()

    @abc.abstractmethod
    def post_execute(self, audit, solution, request_context):
        raise NotImplementedError()


class AuditHandler(BaseAuditHandler, metaclass=abc.ABCMeta):

    def __init__(self):
        super(AuditHandler, self).__init__()
        self._strategy_context = default_context.DefaultStrategyContext()
        self._planner_loader = loader.DefaultPlannerLoader()
        self.applier_client = rpcapi.ApplierAPI()

    def get_planner(self, solution):
        # because AuditHandler is a singletone we need to avoid race condition.
        # thus we need to load planner every time
        planner_name = solution.strategy.planner
        LOG.debug("Loading %s", planner_name)
        planner = self._planner_loader.load(name=planner_name)
        return planner

    @property
    def strategy_context(self):
        return self._strategy_context

    def do_execute(self, audit, request_context):
        # execute the strategy
        solution = self.strategy_context.execute_strategy(
            audit, request_context)

        return solution

    def do_schedule(self, request_context, audit, solution):
        try:
            notifications.audit.send_action_notification(
                request_context, audit,
                action=fields.NotificationAction.PLANNER,
                phase=fields.NotificationPhase.START)
            planner = self.get_planner(solution)
            action_plan = planner.schedule(request_context, audit.id, solution)
            notifications.audit.send_action_notification(
                request_context, audit,
                action=fields.NotificationAction.PLANNER,
                phase=fields.NotificationPhase.END)
            return action_plan
        except Exception:
            notifications.audit.send_action_notification(
                request_context, audit,
                action=fields.NotificationAction.PLANNER,
                priority=fields.NotificationPriority.ERROR,
                phase=fields.NotificationPhase.ERROR)
            raise

    @staticmethod
    def update_audit_state(audit, state):
        if audit.state != state:
            LOG.debug("Update audit state: %s", state)
            audit.state = state
            audit.save()

    @staticmethod
    def check_ongoing_action_plans(request_context):
        a_plan_filters = {'state': objects.action_plan.State.ONGOING}
        ongoing_action_plans = objects.ActionPlan.list(
            request_context, filters=a_plan_filters)
        if ongoing_action_plans:
            raise exception.ActionPlanIsOngoing(
                action_plan=ongoing_action_plans[0].uuid)

    def pre_execute(self, audit, request_context):
        LOG.debug("Trigger audit %s", audit.uuid)
        # If audit.force is true, audit will be executed
        # despite of ongoing actionplan
        if not audit.force:
            self.check_ongoing_action_plans(request_context)
        # Write hostname that will execute this audit.
        audit.hostname = CONF.host
        # change state of the audit to ONGOING
        self.update_audit_state(audit, objects.audit.State.ONGOING)

    def post_execute(self, audit, solution, request_context):
        action_plan = self.do_schedule(request_context, audit, solution)
        if audit.auto_trigger:
            self.applier_client.launch_action_plan(request_context,
                                                   action_plan.uuid)

    def execute(self, audit, request_context):
        try:
            self.pre_execute(audit, request_context)
            solution = self.do_execute(audit, request_context)
            self.post_execute(audit, solution, request_context)
        except exception.ActionPlanIsOngoing as e:
            LOG.warning(e)
            if audit.audit_type == objects.audit.AuditType.ONESHOT.value:
                self.update_audit_state(audit, objects.audit.State.CANCELLED)
        except Exception as e:
            LOG.exception(e)
            self.update_audit_state(audit, objects.audit.State.FAILED)
