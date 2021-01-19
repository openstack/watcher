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


from unittest import mock

from oslo_config import cfg

import oslo_messaging as om
from watcher.common import service
from watcher import objects
from watcher.tests import base

CONF = cfg.CONF


class DummyEndpoint(object):

    def __init__(self, messaging):
        self._messaging = messaging


class DummyManager(object):

    API_VERSION = '1.0'

    conductor_endpoints = [DummyEndpoint]
    notification_endpoints = [DummyEndpoint]

    def __init__(self):
        self.publisher_id = "pub_id"
        self.conductor_topic = "conductor_topic"
        self.notification_topics = []
        self.api_version = self.API_VERSION
        self.service_name = None


class TestServiceHeartbeat(base.TestCase):

    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(objects.Service, 'create')
    def test_send_beat_with_creating_service(self, mock_create,
                                             mock_list):
        CONF.set_default('host', 'fake-fqdn')

        mock_list.return_value = []
        service.ServiceHeartbeat(service_name='watcher-service')
        mock_list.assert_called_once_with(mock.ANY,
                                          filters={'name': 'watcher-service',
                                                   'host': 'fake-fqdn'})
        self.assertEqual(1, mock_create.call_count)

    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(objects.Service, 'save')
    def test_send_beat_without_creating_service(self, mock_save, mock_list):

        mock_list.return_value = [objects.Service(mock.Mock(),
                                                  name='watcher-service',
                                                  host='controller')]
        service.ServiceHeartbeat(service_name='watcher-service')
        self.assertEqual(1, mock_save.call_count)


class TestService(base.TestCase):

    def setUp(self):
        super(TestService, self).setUp()

    @mock.patch.object(om.rpc.server, "RPCServer")
    def test_start(self, m_handler):
        dummy_service = service.Service(DummyManager)
        dummy_service.start()
        self.assertEqual(1, m_handler.call_count)

    @mock.patch.object(om.rpc.server, "RPCServer")
    def test_stop(self, m_handler):
        dummy_service = service.Service(DummyManager)
        dummy_service.stop()
        self.assertEqual(1, m_handler.call_count)

    def test_build_topic_handler(self):
        topic_name = "mytopic"
        dummy_service = service.Service(DummyManager)
        handler = dummy_service.build_topic_handler(topic_name)
        self.assertIsNotNone(handler)
        self.assertIsInstance(handler, om.rpc.server.RPCServer)
        self.assertEqual("mytopic", handler._target.topic)

    def test_init_service(self):
        dummy_service = service.Service(DummyManager)
        self.assertIsInstance(
            dummy_service.conductor_topic_handler,
            om.rpc.server.RPCServer)
