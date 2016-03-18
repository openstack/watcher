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

from watcher.common.messaging import messaging_handler
from watcher.common import rpc
from watcher.common import service
from watcher.tests import base


class DummyManager(object):

    API_VERSION = '1.0'

    conductor_endpoints = []
    status_endpoints = []

    def __init__(self):
        self.publisher_id = "pub_id"
        self.conductor_topic = "conductor_topic"
        self.status_topic = "status_topic"
        self.api_version = self.API_VERSION


class TestService(base.TestCase):

    def setUp(self):
        super(TestService, self).setUp()

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_start(self, m_handler):
        dummy_service = service.Service(DummyManager)
        dummy_service.start()
        self.assertEqual(2, m_handler.call_count)

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_stop(self, m_handler):
        dummy_service = service.Service(DummyManager)
        dummy_service.stop()
        self.assertEqual(2, m_handler.call_count)

    def test_build_topic_handler(self):
        topic_name = "mytopic"
        dummy_service = service.Service(DummyManager)
        handler = dummy_service.build_topic_handler(topic_name)
        self.assertIsNotNone(handler)

    def test_init_service(self):
        dummy_service = service.Service(DummyManager)
        self.assertIsInstance(dummy_service.serializer,
                              rpc.RequestContextSerializer)
        self.assertIsInstance(
            dummy_service.conductor_topic_handler,
            messaging_handler.MessagingHandler)
        self.assertIsInstance(
            dummy_service.status_topic_handler,
            messaging_handler.MessagingHandler)

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_publish_control(self, m_handler_cls):
        m_handler = mock.Mock()
        m_handler_cls.return_value = m_handler
        payload = {
            "name": "value",
        }
        event = "myevent"
        dummy_service = service.Service(DummyManager)
        dummy_service.publish_control(event, payload)
        m_handler.publish_event.assert_called_once_with(event, payload)

    @mock.patch.object(messaging_handler, "MessagingHandler")
    def test_publish_status(self, m_handler_cls):
        m_handler = mock.Mock()
        m_handler_cls.return_value = m_handler
        payload = {
            "name": "value",
        }
        event = "myevent"
        dummy_service = service.Service(DummyManager)
        dummy_service.publish_status(event, payload)
        m_handler.publish_event.assert_called_once_with(event, payload, None)

    @mock.patch.object(service.Service, 'publish_status')
    def test_response(self, mock_call):
        event = "My event"
        context = {'request_id': 12}
        message = "My Message"

        dummy_service = service.Service(DummyManager)
        dummy_service.response(event, context, message)

        expected_payload = {
            'request_id': context['request_id'],
            'msg': message
        }
        mock_call.assert_called_once_with(event, expected_payload)

    def test_messaging_build_topic_handler(self):
        dummy_service = service.Service(DummyManager)
        topic = dummy_service.build_topic_handler("conductor_topic")

        self.assertIsInstance(topic, messaging_handler.MessagingHandler)
        self.assertEqual("pub_id", dummy_service.publisher_id)
        self.assertEqual("pub_id", topic.publisher_id)

        self.assertEqual("conductor_topic",
                         dummy_service.conductor_topic_handler.topic_name)
        self.assertEqual("conductor_topic", topic.topic_name)
