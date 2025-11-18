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

import datetime
from unittest import mock

import freezegun
from oslo_config import cfg
import oslo_messaging as om
from oslo_utils import timeutils

from watcher.common import service
from watcher import objects
from watcher.tests.unit import base
from watcher.tests.unit.db import base as db_base
from watcher.tests.unit.db import utils

CONF = cfg.CONF


class DummyEndpoint:

    def __init__(self, messaging):
        self._messaging = messaging


class DummyManager:

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
        super().setUp()

    @mock.patch.object(om.rpc.server, "RPCServer")
    def _test_start(self, m_handler):
        dummy_service = service.Service(DummyManager)
        dummy_service.start()
        self.assertEqual(1, m_handler.call_count)

    @mock.patch.object(om.rpc.server, "RPCServer")
    def _test_stop(self, m_handler):
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


class TestServiceMonitoringBase(db_base.DbTestCase):

    def setUp(self):
        super().setUp()
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow())
        self.fake_service = objects.Service(**fake_service)

        class DummyServiceMonitoringBase(service.ServiceMonitoringBase):
            def monitor_services_status(self, context):
                pass

        self.monitor = DummyServiceMonitoringBase(
            service_name='watcher-monitored-service')

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_up(self):
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow(),
            last_seen_up=timeutils.utcnow())
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        status = self.monitor.get_service_status(self.context,
                                                 test_service.id)

        self.assertEqual(objects.service.ServiceStatus.ACTIVE, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_down(self):
        past = timeutils.utcnow() - datetime.timedelta(seconds=120)
        fake_service = utils.get_test_service(
            created_at=past,
            last_seen_up=past)
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        status = self.monitor.get_service_status(self.context,
                                                 test_service.id)

        self.assertEqual(objects.service.ServiceStatus.FAILED, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_down_last_seen_up_none(self):
        past = timeutils.utcnow() - datetime.timedelta(seconds=120)
        fake_service = utils.get_test_service(
            created_at=past,
            updated_at=past,
            last_seen_up=None)
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        status = self.monitor.get_service_status(self.context,
                                                 test_service.id)

        self.assertEqual(objects.service.ServiceStatus.FAILED, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_down_updated_at_none(self):
        past = timeutils.utcnow() - datetime.timedelta(seconds=120)
        fake_service = utils.get_test_service(
            created_at=past,
            updated_at=None,
            last_seen_up=None)
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        status = self.monitor.get_service_status(self.context,
                                                 test_service.id)

        self.assertEqual(objects.service.ServiceStatus.FAILED, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_with_string_last_seen_up(self):
        """Test that string timestamps are properly converted."""
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow(),
            last_seen_up="2016-10-18T09:52:05.219414")
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        status = self.monitor.get_service_status(self.context,
                                                 test_service.id)

        self.assertEqual(objects.service.ServiceStatus.ACTIVE, status)

    def test_services_status_tracking(self):
        """Test that services_status dict properly tracks service states."""
        # Initially empty
        self.assertEqual({}, self.monitor.services_status)

        # Add a service status
        self.monitor.services_status[1] = objects.service.ServiceStatus.ACTIVE
        self.assertEqual(
            {1: objects.service.ServiceStatus.ACTIVE},
            self.monitor.services_status
        )

    @mock.patch.object(service.ServiceMonitoringBase,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    def test_get_services_status_without_services_in_list(
            self, mock_get_list, mock_service_status):
        mock_get_list.return_value = []
        services_status = self.monitor.get_services_status(mock.ANY)
        self.assertEqual([], services_status)
        mock_service_status.assert_not_called()

    @mock.patch.object(service.ServiceMonitoringBase,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    def test_get_services_status_with_services_in_list(
            self, m_service_list, m_get_service_status):
        """get_services_status returns only the services with service name."""
        # Create various services
        de_service1 = utils.get_test_service(
            id=1, name='watcher-monitored-service', host='host1')
        de_service2 = utils.get_test_service(
            id=2, name='watcher-monitored-service', host='host2')
        api_service = utils.get_test_service(
            id=3, name='watcher-api', host='host3')
        applier_service = utils.get_test_service(
            id=4, name='watcher-applier', host='host4')

        m_service_list.return_value = [
            objects.Service(**de_service1),
            objects.Service(**de_service2),
            objects.Service(**api_service),
            objects.Service(**applier_service)
        ]
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,
            objects.service.ServiceStatus.FAILED,
            objects.service.ServiceStatus.ACTIVE,
            objects.service.ServiceStatus.ACTIVE
        ]

        result = self.monitor.get_services_status(self.context)

        # Should return all services
        self.assertEqual(2, len(result))
        for wservice in result:
            match wservice.host:
                case 'host1':
                    self.assertEqual(
                        'watcher-monitored-service', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.ACTIVE, wservice.state)
                case 'host2':
                    self.assertEqual(
                        'watcher-monitored-service', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.FAILED, wservice.state)
                case _:
                    self.fail(f'Unexpected host: {wservice.host}')

    def test_am_i_leader_with_single_active_service(self):
        """Test leader election with single active service."""
        # Create service objects with state attribute
        service1 = objects.Service(
            id=1, name='watcher-monitored-service', host='host1')
        service1.state = objects.service.ServiceStatus.ACTIVE

        # Test when current host is the leader
        with mock.patch.object(service.CONF, 'host', 'host1'):
            result = self.monitor._am_i_leader([service1])
            self.assertTrue(result)

        # Test when current host is not the leader
        with mock.patch.object(service.CONF, 'host', 'host2'):
            result = self.monitor._am_i_leader([service1])
            self.assertFalse(result)

    def test_am_i_leader_with_multiple_active_services(self):
        """Test leader election with multiple active services."""
        # Create service objects with state attribute
        # sorted order: host1, host2, host3
        service1 = objects.Service(
            id=1, name='watcher-monitored-service', host='host2')
        service1.state = objects.service.ServiceStatus.ACTIVE
        service2 = objects.Service(
            id=2, name='watcher-monitored-service', host='host1')
        service2.state = objects.service.ServiceStatus.ACTIVE
        service3 = objects.Service(
            id=3, name='watcher-monitored-service', host='host3')
        service3.state = objects.service.ServiceStatus.ACTIVE

        # Leader should be host1 (alphabetically first)
        with mock.patch.object(service.CONF, 'host', 'host1'):
            result = self.monitor._am_i_leader([service1, service2, service3])
            self.assertTrue(result)

        with mock.patch.object(service.CONF, 'host', 'host2'):
            result = self.monitor._am_i_leader([service1, service2, service3])
            self.assertFalse(result)

        with mock.patch.object(service.CONF, 'host', 'host3'):
            result = self.monitor._am_i_leader([service1, service2, service3])
            self.assertFalse(result)

    def test_am_i_leader_with_failed_services(self):
        """Test leader election ignores failed services."""
        # Create service objects with mixed states
        service1 = objects.Service(
            id=1, name='watcher-monitored-service', host='host1')
        service1.state = objects.service.ServiceStatus.FAILED
        service2 = objects.Service(
            id=2, name='watcher-monitored-service', host='host2')
        service2.state = objects.service.ServiceStatus.ACTIVE

        # Leader should be host2 (only active service)
        with mock.patch.object(service.CONF, 'host', 'host2'):
            result = self.monitor._am_i_leader([service1, service2])
            self.assertTrue(result)

        with mock.patch.object(service.CONF, 'host', 'host1'):
            result = self.monitor._am_i_leader([service1, service2])
            self.assertFalse(result)

    def test_am_i_leader_with_failed_services_changes(self):
        """Test leader election ignores failed services."""
        # Create service objects with mixed states
        service1 = objects.Service(
            id=1, name='watcher-monitored-service', host='host1')
        service1.state = objects.service.ServiceStatus.FAILED
        service2 = objects.Service(
            id=2, name='watcher-monitored-service', host='host2')
        service2.state = objects.service.ServiceStatus.ACTIVE

        # Leader should be host2 (only active service)
        with mock.patch.object(service.CONF, 'host', 'host2'):
            result = self.monitor._am_i_leader([service1, service2])
            self.assertTrue(result)

        with mock.patch.object(service.CONF, 'host', 'host1'):
            result = self.monitor._am_i_leader([service1, service2])
            self.assertFalse(result)

        service1.state = objects.service.ServiceStatus.ACTIVE
        service2.state = objects.service.ServiceStatus.FAILED
        # Leader should be host1 (only active service)
        with mock.patch.object(service.CONF, 'host', 'host2'):
            result = self.monitor._am_i_leader([service1, service2])
            self.assertFalse(result)

        with mock.patch.object(service.CONF, 'host', 'host1'):
            result = self.monitor._am_i_leader([service1, service2])
            self.assertTrue(result)

    def test_am_i_leader_with_no_active_services(self):
        """Test leader election when no services are active."""
        # Create service objects with all failed states
        service1 = objects.Service(
            id=1, name='watcher-monitored-service', host='host1')
        service1.state = objects.service.ServiceStatus.FAILED
        service2 = objects.Service(
            id=2, name='watcher-monitored-service', host='host2')
        service2.state = objects.service.ServiceStatus.FAILED

        # Should return False when no services are active
        with mock.patch.object(service.CONF, 'host', 'host1'):
            result = self.monitor._am_i_leader([service1, service2])
            self.assertFalse(result)
