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

import exceptions

from watcher.decision_engine.framework.events.event_consumer_factory import \
    EventConsumerFactory
from watcher.decision_engine.framework.messaging.events import Events
from watcher.tests import base


class TestEventConsumerFactory(base.TestCase):

    event_consumer_factory = EventConsumerFactory()

    def test_factory_with_unknown_type(self):
        self.assertRaises(exceptions.AssertionError,
                          self.event_consumer_factory.factory,
                          Events.ALL)
