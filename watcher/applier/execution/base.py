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

from watcher.applier.messaging import events
from watcher.applier.primitives import factory
from watcher.common.messaging.events import event
from watcher import objects


@six.add_metaclass(abc.ABCMeta)
class BaseActionPlanExecutor(object):
    def __init__(self, manager_applier, context):
        self._manager_applier = manager_applier
        self._context = context
        self._action_factory = factory.ActionFactory()

    @property
    def context(self):
        return self._context

    @property
    def manager_applier(self):
        return self._manager_applier

    @property
    def action_factory(self):
        return self._action_factory

    def notify(self, action, state):
        db_action = objects.Action.get_by_uuid(self.context, action.uuid)
        db_action.state = state
        db_action.save()
        ev = event.Event()
        ev.type = events.Events.LAUNCH_ACTION
        ev.data = {}
        payload = {'action_uuid': action.uuid,
                   'action_state': state}
        self.manager_applier.topic_status.publish_event(ev.type.name,
                                                        payload)

    @abc.abstractmethod
    def execute(self, actions):
        raise NotImplementedError()
