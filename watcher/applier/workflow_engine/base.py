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
from watcher.common.messaging.events import event
from watcher import objects


@six.add_metaclass(abc.ABCMeta)
class BaseWorkFlowEngine(object):
    def __init__(self):
        self._applier_manager = None
        self._context = None
        self._action_factory = factory.ActionFactory()

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, c):
        self._context = c

    @property
    def applier_manager(self):
        return self._applier_manager

    @applier_manager.setter
    def applier_manager(self, a):
        self._applier_manager = a

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
        self.applier_manager.topic_status.publish_event(ev.type.name,
                                                        payload)

    @abc.abstractmethod
    def execute(self, actions):
        raise NotImplementedError()
