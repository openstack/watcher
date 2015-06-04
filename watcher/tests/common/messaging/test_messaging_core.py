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
from oslo_config import cfg

from watcher.common.messaging.messaging_core import MessagingCore
from watcher.common.messaging.messaging_handler import MessagingHandler
from watcher.common.rpc import RequestContextSerializer
from watcher.tests import base

CONF = cfg.CONF


class TestMessagingCore(base.TestCase):
    messaging = MessagingCore("", "", "")

    def fake_topic_name(self):
        topic_name = "MyTopic"
        return topic_name

    def test_build_topic(self):
        topic_name = self.fake_topic_name()
        messaging_handler = self.messaging.build_topic(topic_name)
        self.assertIsNotNone(messaging_handler)

    def test_init_messaging_core(self):
        self.assertIsInstance(self.messaging.serializer,
                              RequestContextSerializer)
        self.assertIsInstance(self.messaging.topic_control, MessagingHandler)
        self.assertIsInstance(self.messaging.topic_status, MessagingHandler)

    def test_publish_control(self):
        with mock.patch.object(MessagingCore, 'publish_control') as mock_call:
            payload = {
                "name": "value",
            }
            event = "MyEvent"
            self.messaging.publish_control(event, payload)
            mock_call.assert_called_once_with(event, payload)

    def test_publish_status(self):
        with mock.patch.object(MessagingCore, 'publish_status') as mock_call:
            payload = {
                "name": "value",
            }
            event = "MyEvent"
            self.messaging.publish_status(event, payload)
            mock_call.assert_called_once_with(event, payload)

    def test_response(self):
        with mock.patch.object(MessagingCore, 'publish_status') as mock_call:
            event = "My event"
            context = {'request_id': 12}
            message = "My Message"

            self.messaging.response(event, context, message)

            expected_payload = {
                'request_id': context['request_id'],
                'msg': message
            }
            mock_call.assert_called_once_with(event, expected_payload)
