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

from oslo_log import log
import six
from taskflow import task as flow_task

from watcher._i18n import _LE
from watcher.applier.actions import factory
from watcher.common import clients
from watcher.common.loader import loadable
from watcher import notifications
from watcher import objects
from watcher.objects import fields


LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseWorkFlowEngine(loadable.Loadable):

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

    # NOTE(alexchadin): taskflow does 3 method calls (pre_execute, execute,
    # post_execute) independently. We want to support notifications in base
    # class, so child's methods should be named with `do_` prefix and wrapped.
    def pre_execute(self):
        try:
            self.do_pre_execute()
            notifications.action.send_execution_notification(
                self.engine.context, self._db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.START)
        except Exception as e:
            LOG.exception(e)
            self.engine.notify(self._db_action, objects.action.State.FAILED)
            notifications.action.send_execution_notification(
                self.engine.context, self._db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.ERROR,
                priority=fields.NotificationPriority.ERROR)

    def execute(self, *args, **kwargs):
        try:
            self.do_execute(*args, **kwargs)
            notifications.action.send_execution_notification(
                self.engine.context, self._db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.END)
        except Exception as e:
            LOG.exception(e)
            LOG.error(_LE('The workflow engine has failed '
                          'to execute the action: %s'), self.name)
            self.engine.notify(self._db_action, objects.action.State.FAILED)
            notifications.action.send_execution_notification(
                self.engine.context, self._db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.ERROR,
                priority=fields.NotificationPriority.ERROR)
            raise

    def post_execute(self):
        try:
            self.do_post_execute()
        except Exception as e:
            LOG.exception(e)
            self.engine.notify(self._db_action, objects.action.State.FAILED)
            notifications.action.send_execution_notification(
                self.engine.context, self._db_action,
                fields.NotificationAction.EXECUTION,
                fields.NotificationPhase.ERROR,
                priority=fields.NotificationPriority.ERROR)
