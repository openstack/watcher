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

import mock

from watcher.common import utils

from watcher.decision_engine.framework.events.event_consumer_factory import \
    EventConsumerFactory

from watcher.common.messaging.events.event import Event
from watcher.decision_engine.framework.manager_decision_engine import \
    DecisionEngineManager

from watcher.decision_engine.framework.messaging.events import Events
from watcher.tests import base


class TestDecisionEngineManager(base.TestCase):
    def setUp(self):
        super(TestDecisionEngineManager, self).setUp()
        self.manager = DecisionEngineManager()

    def test_event_receive(self):
        # todo(jed) remove useless
        with mock.patch.object(EventConsumerFactory, 'factory') as mock_call:
            data = {"key1": "value"}
            request_id = utils.generate_uuid()
            event_type = Events.TRIGGER_AUDIT
            event = Event(event_type, data, request_id)
            self.manager.event_receive(event)
            mock_call.assert_called_once_with(event_type)
