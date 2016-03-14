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

from watcher.common.messaging import messaging_core
from watcher.common.messaging import messaging_handler
from watcher.common import rpc
from watcher.tests import base


class TestMessagingCore(base.TestCase):

    def setUp(self):
        super(TestMessagingCore, self).setUp()

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_connect(self, m_handler):
        messaging = messaging_core.MessagingCore("", "", "")
        messaging.connect()
        self.assertEqual(2, m_handler.call_count)

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_disconnect(self, m_handler):
        messaging = messaging_core.MessagingCore("", "", "")
        messaging.disconnect()
        self.assertEqual(2, m_handler.call_count)

    def test_build_topic_handler(self):
        topic_name = "MyTopic"
        messaging = messaging_core.MessagingCore("", "", "")
        handler = messaging.build_topic_handler(topic_name)
        self.assertIsNotNone(handler)

    def test_init_messaging_core(self):
        messaging = messaging_core.MessagingCore("", "", "")
        self.assertIsInstance(messaging.serializer,
                              rpc.RequestContextSerializer)
        self.assertIsInstance(
            messaging.conductor_topic_handler,
            messaging_handler.MessagingHandler)
        self.assertIsInstance(
            messaging.status_topic_handler,
            messaging_handler.MessagingHandler)

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_publish_control(self, m_handler_cls):
        m_handler = mock.Mock()
        m_handler_cls.return_value = m_handler
        payload = {
            "name": "value",
        }
        event = "MyEvent"
        messaging = messaging_core.MessagingCore("", "", "")
        messaging.publish_control(event, payload)
        m_handler.publish_event.assert_called_once_with(event, payload)

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_publish_status(self, m_handler_cls):
        m_handler = mock.Mock()
        m_handler_cls.return_value = m_handler
        payload = {
            "name": "value",
        }
        event = "MyEvent"
        messaging = messaging_core.MessagingCore("", "", "")
        messaging.publish_status(event, payload)
        m_handler.publish_event.assert_called_once_with(event, payload, None)

    @mock.patch.object(messaging_core.MessagingCore, 'publish_status')
    def test_response(self, mock_call):
        event = "My event"
        context = {'request_id': 12}
        message = "My Message"

        messaging = messaging_core.MessagingCore("", "", "")
        messaging.response(event, context, message)

        expected_payload = {
            'request_id': context['request_id'],
            'msg': message
        }
        mock_call.assert_called_once_with(event, expected_payload)

    def test_messaging_build_topic_handler(self):
        messaging = messaging_core.MessagingCore(
            "pub_id", "test_topic", "does not matter")
        topic = messaging.build_topic_handler("test_topic")

        self.assertIsInstance(topic, messaging_handler.MessagingHandler)
        self.assertEqual("pub_id", messaging.publisher_id)
        self.assertEqual("pub_id", topic.publisher_id)

        self.assertEqual("test_topic",
                         messaging.conductor_topic_handler.topic_name)
        self.assertEqual("test_topic", topic.topic_name)
