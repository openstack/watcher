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
from mock import call
from mock import MagicMock
from watcher.common.messaging.events.event import Event
from watcher.common.messaging.events.event_dispatcher import EventDispatcher
from watcher.decision_engine.framework.messaging.events import Events
from watcher.tests import base


class TestEventDispatcher(base.TestCase):

    def setUp(self):
        super(TestEventDispatcher, self).setUp()
        self.event_dispatcher = EventDispatcher()

    def fake_listener(self):
        return MagicMock()

    def fake_event(self, event_type):
        event = Event()
        event.set_type(event_type)
        return event

    def test_add_listener(self):
        listener = self.fake_listener()
        self.event_dispatcher.add_event_listener(Events.ALL,
                                                 listener)

        self.assertEqual(True, self.event_dispatcher.has_listener(
            Events.ALL, listener))

    def test_remove_listener(self):
        listener = self.fake_listener()
        self.event_dispatcher.add_event_listener(Events.ALL,
                                                 listener)
        self.event_dispatcher.remove_event_listener(Events.ALL, listener)

        self.assertEqual(False, self.event_dispatcher.has_listener(
            Events.TRIGGER_AUDIT, listener))

    def test_dispatch_event(self):
        listener = self.fake_listener()
        event = self.fake_event(Events.TRIGGER_AUDIT)
        self.event_dispatcher.add_event_listener(Events.TRIGGER_AUDIT,
                                                 listener)

        self.event_dispatcher.dispatch_event(event)
        listener.assert_has_calls(calls=[call(event)])

    def test_dispatch_event_to_all_listener(self):
        event = self.fake_event(Events.ACTION_PLAN)
        listener_all = self.fake_listener()
        listener_action_plan = self.fake_listener()
        listener_trigger_audit = self.fake_listener()

        self.event_dispatcher.add_event_listener(Events.ALL, listener_all)
        self.event_dispatcher.add_event_listener(Events.ACTION_PLAN,
                                                 listener_action_plan)

        self.event_dispatcher.add_event_listener(Events.TRIGGER_AUDIT,
                                                 listener_trigger_audit)

        self.event_dispatcher.dispatch_event(event)
        listener_all.assert_has_calls(calls=[call(event)])
        listener_action_plan.assert_has_calls(calls=[call(event)])
        listener_trigger_audit.assert_has_calls([])
