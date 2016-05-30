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

import six

from watcher.applier.actions import factory
from watcher.applier.messaging import event_types
from watcher.common import clients
from watcher.common.loader import loadable
from watcher.common.messaging.events import event
from watcher import objects


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
        db_action = objects.Action.get_by_uuid(self.context, action.uuid)
        db_action.state = state
        db_action.save()
        ev = event.Event()
        ev.type = event_types.EventTypes.LAUNCH_ACTION
        ev.data = {}
        payload = {'action_uuid': action.uuid,
                   'action_state': state}
        self.applier_manager.status_topic_handler.publish_event(
            ev.type.name, payload)

    @abc.abstractmethod
    def execute(self, actions):
        raise NotImplementedError()
