# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import mock
from oslo_serialization import jsonutils

from watcher.common import context
from watcher.common import service as watcher_service
from watcher.decision_engine.model.notification import base
from watcher.decision_engine.model.notification import filtering
from watcher.tests import base as base_test
from watcher.tests.decision_engine.model.notification import fake_managers


class DummyManager(fake_managers.FakeManager):

    @property
    def notification_endpoints(self):
        return [DummyNotification(self.fake_cdmc)]


class DummyNotification(base.NotificationEndpoint):

    @property
    def filter_rule(self):
        return filtering.NotificationFilter(
            publisher_id=r'.*',
            event_type=r'compute.dummy',
            payload={'data': {'nested': r'^T.*'}},
        )

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        pass


class NotificationTestCase(base_test.TestCase):

    def load_message(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as json_file:
            json_data = jsonutils.load(json_file)

        return json_data


class TestReceiveNotifications(NotificationTestCase):

    def setUp(self):
        super(TestReceiveNotifications, self).setUp()

        p_from_dict = mock.patch.object(context.RequestContext, 'from_dict')
        m_from_dict = p_from_dict.start()
        m_from_dict.return_value = self.context
        self.addCleanup(p_from_dict.stop)

    @mock.patch.object(watcher_service.ServiceHeartbeat, 'send_beat')
    @mock.patch.object(DummyNotification, 'info')
    def test_receive_dummy_notification(self, m_info, m_heartbeat):
        message = {
            'publisher_id': 'nova-compute',
            'event_type': 'compute.dummy',
            'payload': {'data': {'nested': 'TEST'}},
            'priority': 'INFO',
        }
        de_service = watcher_service.Service(DummyManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)

        m_info.assert_called_once_with(
            self.context, 'nova-compute', 'compute.dummy',
            {'data': {'nested': 'TEST'}},
            {'message_id': None, 'timestamp': None})

    @mock.patch.object(watcher_service.ServiceHeartbeat, 'send_beat')
    @mock.patch.object(DummyNotification, 'info')
    def test_skip_unwanted_notification(self, m_info, m_heartbeat):
        message = {
            'publisher_id': 'nova-compute',
            'event_type': 'compute.dummy',
            'payload': {'data': {'nested': 'unwanted'}},
            'priority': 'INFO',
        }
        de_service = watcher_service.Service(DummyManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)

        self.assertEqual(0, m_info.call_count)
