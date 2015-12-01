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

from mock import Mock
from mock import patch
from oslo_config import cfg
import oslo_messaging as messaging
from watcher.common.messaging.messaging_handler import MessagingHandler
from watcher.tests.base import TestCase

CONF = cfg.CONF


class TestMessagingHandler(TestCase):

    PUBLISHER_ID = 'TEST_API'
    TOPIC_WATCHER = 'TEST_TOPIC_WATCHER'
    ENDPOINT = 'http://fake-fqdn:1337'
    VERSION = "1.0"

    def setUp(self):
        super(TestMessagingHandler, self).setUp()
        CONF.set_default('host', 'fake-fqdn')

    @patch.object(messaging, "get_rpc_server")
    @patch.object(messaging, "Target")
    def test_setup_messaging_handler(self, m_target_cls, m_get_rpc_server):
        m_target = Mock()
        m_target_cls.return_value = m_target
        messaging_handler = MessagingHandler(
            publisher_id=self.PUBLISHER_ID,
            topic_watcher=self.TOPIC_WATCHER,
            endpoint=self.ENDPOINT,
            version=self.VERSION,
            serializer=None,
        )

        messaging_handler.run()

        m_target_cls.assert_called_once_with(
            server="fake-fqdn",
            topic="TEST_TOPIC_WATCHER",
            version="1.0",
        )
        m_get_rpc_server.assert_called_once_with(
            messaging_handler.transport,
            m_target,
            [self.ENDPOINT],
            serializer=None,
        )

    def test_messaging_handler_remove_endpoint(self):
        messaging_handler = MessagingHandler(
            publisher_id=self.PUBLISHER_ID,
            topic_watcher=self.TOPIC_WATCHER,
            endpoint=self.ENDPOINT,
            version=self.VERSION,
            serializer=None,
        )

        self.assertEqual(messaging_handler.endpoints, [self.ENDPOINT])

        messaging_handler.remove_endpoint(self.ENDPOINT)

        self.assertEqual(messaging_handler.endpoints, [])
