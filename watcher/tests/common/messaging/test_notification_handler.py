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
from oslo import messaging
from watcher.common.messaging.notification_handler import NotificationHandler
from watcher.common.messaging.utils.observable import Observable
from watcher.tests import base

PUBLISHER_ID = 'TEST_API'


class TestNotificationHandler(base.TestCase):

    def setUp(self):
        super(TestNotificationHandler, self).setUp()
        self.notification_handler = NotificationHandler(PUBLISHER_ID)

    def _test_notify(self, level_to_call):
        ctx = {}
        publisher_id = PUBLISHER_ID
        event_type = 'Test'
        payload = {}
        metadata = {}

        with mock.patch.object(Observable, 'notify') as mock_call:
            notification_result = level_to_call(ctx, publisher_id, event_type,
                                                payload, metadata)
            self.assertEqual(messaging.NotificationResult.HANDLED,
                             notification_result)
            mock_call.assert_called_once_with(ctx, publisher_id, event_type,
                                              metadata, payload)

    def test_notify_info(self):
        self._test_notify(self.notification_handler.info)

    def test_notify_warn(self):
        self._test_notify(self.notification_handler.warn)

    def test_notify_error(self):
        self._test_notify(self.notification_handler.error)
