# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
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
import time

import eventlet

from oslo_log import log
from taskflow import task as flow_task

from watcher.applier.actions import factory
from watcher.common import clients
from watcher.common import exception
from watcher.common.loader import loadable
from watcher import notifications
from watcher import objects
from watcher.objects import fields


LOG = log.getLogger(__name__)

CANCEL_STATE = [objects.action_plan.State.CANCELLING,
                objects.action_plan.State.CANCELLED]


class BaseWorkFlowEngine(loadable.Loadable, metaclass=abc.ABCMeta):

    def __init__(self, config, context=None, applier_manager=None):
        """Constructor

        :param config: A mapping containing the configuration of this
                       workflow engine
        :type config: dict
        :param osc: an OpenStackClients object, defaults to None
        :type osc: :py:class:`~.OpenStackClients` instance, optional
        """
        super(BaseWorkFlowEngine, self).__init__(config)
        self._context = context
        self._applier_manager = applier_manager
        self._action_factory = factory.ActionFactory()
        self._osc = None
        self._is_notified = False
        self.execution_rule = None

    @classmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        return []

    @property
    def context(self):
        return self._context

    @property
    def osc(self):
        if not self._osc:
            self._osc = clients.OpenStackClients()
        return self._osc

    @property
    def applier_manager(self):
        return self._applier_manager

    @property
    def action_factory(self):
        return self._action_factory

    def notify(self, action, state):
        db_action = objects.Action.get_by_uuid(self.context, action.uuid,
                                               eager=True)
        db_action.state = state
        db_action.save()
        return db_action

    def notify_cancel_start(self, action_plan_uuid):
        action_plan = objects.ActionPlan.get_by_uuid(self.context,
                                                     action_plan_uuid,
                                                     eager=True)
        if not self._is_notified:
            self._is_notified = True
            notifications.action_plan.send_cancel_notification(
                self._context, action_plan,
                action=fields.NotificationAction.CANCEL,
                phase=fields.NotificationPhase.START)

    @abc.abstractmethod
    def execute(self, actions):
        raise NotImplementedError()


class BaseTaskFlowActionContainer(flow_task.Task):

    def __init__(self, name, db_action, engine, **kwargs):
        super(BaseTaskFlowActionContainer, self).__init__(name=name)
        self._db_action = db_action
        self._engine = engine
        self.loaded_action = None

    @property
    def engine(self):
        return self._engine

    @property
    def action(self):
        if self.loaded_action is None:
            action = self.engine.action_factory.make_action(
                self._db_action,
                osc=self._engine.osc)
            self.loaded_action = action
        return self.loaded_action

    @abc.abstractmethod
    def do_pre_execute(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def do_execute(self, *args, **kwargs):
        raise NotImplementedError()

    @abc.abstractmethod
    def do_post_execute(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def do_revert(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def do_abort(self, *args, **kwargs):
        raise NotImplementedError()

    # NOTE(alexchadin): taskflow does 3 method calls (pre_execute, execute,
    # post_execute) independently. We want to support notifications in base
    # class, so child's methods should be named with `do_` prefix and wrapped.
    def pre_execute(self):
        try:
            # NOTE(adisky): check the state of action plan before starting
            # next action, if action plan is cancelled raise the exceptions
            # so that taskflow does not schedule further actions.
            action_plan = objects.ActionPlan.get_by_id(
                self.engine.context, self._db_action.action_plan_id)
            if action_plan.state in CANCEL_STATE:
                raise exception.ActionPlanCancelled(uuid=action_plan.uuid)
            db_action = self.do_pre_execute()
            notifications.action.send_execution_notification(
                self.engine.context, db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.START)
        except exception.ActionPlanCancelled as e:
            LOG.exception(e)
            self.engine.notify_cancel_start(action_plan.uuid)
            raise
        except Exception as e:
            LOG.exception(e)
            db_action = self.engine.notify(self._db_action,
                                           objects.action.State.FAILED)
            notifications.action.send_execution_notification(
                self.engine.context, db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.ERROR,
                priority=fields.NotificationPriority.ERROR)

    def execute(self, *args, **kwargs):
        def _do_execute_action(*args, **kwargs):
            try:
                db_action = self.do_execute(*args, **kwargs)
                notifications.action.send_execution_notification(
                    self.engine.context, db_action,
                    fields.NotificationAction.EXECUTION,
                    fields.NotificationPhase.END)
            except Exception as e:
                LOG.exception(e)
                LOG.error('The workflow engine has failed '
                          'to execute the action: %s', self.name)
                db_action = self.engine.notify(self._db_action,
                                               objects.action.State.FAILED)
                notifications.action.send_execution_notification(
                    self.engine.context, db_action,
                    fields.NotificationAction.EXECUTION,
                    fields.NotificationPhase.ERROR,
                    priority=fields.NotificationPriority.ERROR)
                raise
        # NOTE: spawn a new thread for action execution, so that if action plan
        # is cancelled workflow engine will not wait to finish action execution
        et = eventlet.spawn(_do_execute_action, *args, **kwargs)
        # NOTE: check for the state of action plan periodically,so that if
        # action is finished or action plan is cancelled we can exit from here.
        result = False
        while True:
            action_object = objects.Action.get_by_uuid(
                self.engine.context, self._db_action.uuid, eager=True)
            action_plan_object = objects.ActionPlan.get_by_id(
                self.engine.context, action_object.action_plan_id)
            if action_object.state == objects.action.State.SUCCEEDED:
                result = True
            if (action_object.state in [objects.action.State.SUCCEEDED,
               objects.action.State.FAILED] or
               action_plan_object.state in CANCEL_STATE):
                break
            time.sleep(1)
        try:
            # NOTE: kill the action execution thread, if action plan is
            # cancelled for all other cases wait for the result from action
            # execution thread.
            # Not all actions support abort operations, kill only those action
            # which support abort operations
            abort = self.action.check_abort()
            if (action_plan_object.state in CANCEL_STATE and abort):
                et.kill()
            et.wait()
            return result

            # NOTE: catch the greenlet exit exception due to thread kill,
            # taskflow will call revert for the action,
            # we will redirect it to abort.
        except eventlet.greenlet.GreenletExit:
            self.engine.notify_cancel_start(action_plan_object.uuid)
            raise exception.ActionPlanCancelled(uuid=action_plan_object.uuid)

        except Exception as e:
            LOG.exception(e)
            # return False instead of raising an exception
            return False

    def post_execute(self):
        try:
            self.do_post_execute()
        except Exception as e:
            LOG.exception(e)
            db_action = self.engine.notify(self._db_action,
                                           objects.action.State.FAILED)
            notifications.action.send_execution_notification(
                self.engine.context, db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.ERROR,
                priority=fields.NotificationPriority.ERROR)

    def revert(self, *args, **kwargs):
        action_plan = objects.ActionPlan.get_by_id(
            self.engine.context, self._db_action.action_plan_id, eager=True)
        # NOTE: check if revert cause by cancel action plan or
        # some other exception occurred during action plan execution
        # if due to some other exception keep the flow intact.
        if action_plan.state not in CANCEL_STATE:
            self.do_revert()
            return

        action_object = objects.Action.get_by_uuid(
            self.engine.context, self._db_action.uuid, eager=True)
        try:
            if action_object.state == objects.action.State.ONGOING:
                action_object.state = objects.action.State.CANCELLING
                action_object.save()
                notifications.action.send_cancel_notification(
                    self.engine.context, action_object,
                    fields.NotificationAction.CANCEL,
                    fields.NotificationPhase.START)
                action_object = self.abort()

                notifications.action.send_cancel_notification(
                    self.engine.context, action_object,
                    fields.NotificationAction.CANCEL,
                    fields.NotificationPhase.END)

            if action_object.state == objects.action.State.PENDING:
                notifications.action.send_cancel_notification(
                    self.engine.context, action_object,
                    fields.NotificationAction.CANCEL,
                    fields.NotificationPhase.START)
                action_object.state = objects.action.State.CANCELLED
                action_object.save()
                notifications.action.send_cancel_notification(
                    self.engine.context, action_object,
                    fields.NotificationAction.CANCEL,
                    fields.NotificationPhase.END)

        except Exception as e:
            LOG.exception(e)
            action_object.state = objects.action.State.FAILED
            action_object.save()
            notifications.action.send_cancel_notification(
                self.engine.context, action_object,
                fields.NotificationAction.CANCEL,
                fields.NotificationPhase.ERROR,
                priority=fields.NotificationPriority.ERROR)

    def abort(self, *args, **kwargs):
        return self.do_abort(*args, **kwargs)
