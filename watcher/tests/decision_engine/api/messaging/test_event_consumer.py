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

from watcher.decision_engine.api.messaging.event_consumer import EventConsumer
from watcher.tests import base


class TestEventConsumer(base.TestCase):
    def test_set_messaging(self):
        messaging = "test message"
        EC = EventConsumer()
        EC.set_messaging(messaging)
        self.assertEqual(EC.messaging, messaging)

    def test_execute(self):
        EC = EventConsumer()
        self.assertRaises(NotImplementedError, EC.execute, None, None, None)
