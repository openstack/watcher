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


from mock import patch

from watcher.common.messaging.messaging_core import MessagingCore
from watcher.common.messaging.messaging_handler import MessagingHandler
from watcher.common.rpc import RequestContextSerializer
from watcher.tests.base import TestCase


class TestMessagingCore(TestCase):

    def setUp(self):
        super(TestMessagingCore, self).setUp()

    def test_build_topic(self):
        topic_name = "MyTopic"
        messaging = MessagingCore("", "", "")
        messaging_handler = messaging.build_topic(topic_name)
        self.assertIsNotNone(messaging_handler)

    def test_init_messaging_core(self):
        messaging = MessagingCore("", "", "")
        self.assertIsInstance(messaging.serializer,
                              RequestContextSerializer)
        self.assertIsInstance(messaging.topic_control, MessagingHandler)
        self.assertIsInstance(messaging.topic_status, MessagingHandler)

    @patch.object(MessagingCore, 'publish_control')
    def test_publish_control(self, mock_call):
        payload = {
            "name": "value",
        }
        event = "MyEvent"
        messaging = MessagingCore("", "", "")
        messaging.publish_control(event, payload)
        mock_call.assert_called_once_with(event, payload)

    @patch.object(MessagingCore, 'publish_status')
    def test_publish_status(self, mock_call):
        payload = {
            "name": "value",
        }
        event = "MyEvent"
        messaging = MessagingCore("", "", "")
        messaging.publish_status(event, payload)
        mock_call.assert_called_once_with(event, payload)

    @patch.object(MessagingCore, 'publish_status')
    def test_response(self, mock_call):
        event = "My event"
        context = {'request_id': 12}
        message = "My Message"

        messaging = MessagingCore("", "", "")
        messaging.response(event, context, message)

        expected_payload = {
            'request_id': context['request_id'],
            'msg': message
        }
        mock_call.assert_called_once_with(event, expected_payload)

    def test_messaging_build_topic(self):
        messaging = MessagingCore("pub_id", "test_topic", "does not matter")
        topic = messaging.build_topic("test_topic")

        self.assertIsInstance(topic, MessagingHandler)
        self.assertEqual(messaging.publisher_id, "pub_id")
        self.assertEqual(topic.publisher_id, "pub_id")

        self.assertEqual(messaging.topic_control.topic_watcher, "test_topic")
        self.assertEqual(topic.topic_watcher, "test_topic")
