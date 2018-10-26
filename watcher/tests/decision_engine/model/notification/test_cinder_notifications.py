# -*- encoding: utf-8 -*-
# Copyright 2017 NEC Corporation
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

import datetime
import os

import mock
from oslo_serialization import jsonutils

from watcher.common import cinder_helper
from watcher.common import context
from watcher.common import exception
from watcher.common import service as watcher_service
from watcher.db.sqlalchemy import api as db_api
from watcher.decision_engine.model.notification import cinder as cnotification
from watcher.tests import base as base_test
from watcher.tests.db import utils
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.model.notification import fake_managers


class NotificationTestCase(base_test.TestCase):

    @staticmethod
    def load_message(filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as json_file:
            json_data = jsonutils.load(json_file)

        return json_data


class TestReceiveCinderNotifications(NotificationTestCase):

    FAKE_METADATA = {'message_id': None, 'timestamp': None}

    def setUp(self):
        super(TestReceiveCinderNotifications, self).setUp()

        p_from_dict = mock.patch.object(context.RequestContext, 'from_dict')
        m_from_dict = p_from_dict.start()
        m_from_dict.return_value = self.context
        self.addCleanup(p_from_dict.stop)

        p_get_service_list = mock.patch.object(
            db_api.Connection, 'get_service_list')
        p_update_service = mock.patch.object(
            db_api.Connection, 'update_service')
        m_get_service_list = p_get_service_list.start()
        m_update_service = p_update_service.start()
        fake_service = utils.get_test_service(
            created_at=datetime.datetime.utcnow())

        m_get_service_list.return_value = [fake_service]
        m_update_service.return_value = fake_service.copy()

        self.addCleanup(p_get_service_list.stop)
        self.addCleanup(p_update_service.stop)

    @mock.patch.object(cnotification.CapacityNotificationEndpoint, 'info')
    def test_cinder_receive_capacity(self, m_info):
        message = self.load_message('capacity.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeStorageManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'capacity.host1@backend1#pool1', 'capacity.pool',
            expected_message, self.FAKE_METADATA)

    @mock.patch.object(cnotification.VolumeCreateEnd, 'info')
    def test_cinder_receive_volume_create_end(self, m_info):
        message = self.load_message('scenario_1_volume-create.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeStorageManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'volume.host_0@backend_0#pool_0',
            'volume.create.end', expected_message, self.FAKE_METADATA)

    @mock.patch.object(cnotification.VolumeUpdateEnd, 'info')
    def test_cinder_receive_volume_update_end(self, m_info):
        message = self.load_message('scenario_1_volume-update.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeStorageManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'volume.host_0@backend_0#pool_0',
            'volume.update.end', expected_message, self.FAKE_METADATA)

    @mock.patch.object(cnotification.VolumeAttachEnd, 'info')
    def test_cinder_receive_volume_attach_end(self, m_info):
        message = self.load_message('scenario_1_volume-attach.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeStorageManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'volume.host_0@backend_0#pool_0',
            'volume.attach.end', expected_message, self.FAKE_METADATA)

    @mock.patch.object(cnotification.VolumeDetachEnd, 'info')
    def test_cinder_receive_volume_detach_end(self, m_info):
        message = self.load_message('scenario_1_volume-detach.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeStorageManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'volume.host_0@backend_0#pool_0',
            'volume.detach.end', expected_message, self.FAKE_METADATA)

    @mock.patch.object(cnotification.VolumeResizeEnd, 'info')
    def test_cinder_receive_volume_resize_end(self, m_info):
        message = self.load_message('scenario_1_volume-resize.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeStorageManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'volume.host_0@backend_0#pool_0',
            'volume.resize.end', expected_message, self.FAKE_METADATA)

    @mock.patch.object(cnotification.VolumeDeleteEnd, 'info')
    def test_cinder_receive_volume_delete_end(self, m_info):
        message = self.load_message('scenario_1_volume-delete.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeStorageManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'volume.host_0@backend_0#pool_0',
            'volume.delete.end', expected_message, self.FAKE_METADATA)


class TestCinderNotifications(NotificationTestCase):

    FAKE_METADATA = {'message_id': None, 'timestamp': None}

    def setUp(self):
        super(TestCinderNotifications, self).setUp()
        # fake cluster
        self.fake_cdmc = faker_cluster_state.FakerStorageModelCollector()

    def test_cinder_capacity(self):
        """test consuming capacity"""

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.CapacityNotificationEndpoint(self.fake_cdmc)

        pool_0_name = 'host_0@backend_0#pool_0'
        pool_0 = storage_model.get_pool_by_pool_name(pool_0_name)

        # before
        self.assertEqual(pool_0_name, pool_0.name)
        self.assertEqual(420, pool_0.free_capacity_gb)
        self.assertEqual(420, pool_0.virtual_free)
        self.assertEqual(80, pool_0.allocated_capacity_gb)
        self.assertEqual(80, pool_0.provisioned_capacity_gb)

        message = self.load_message('scenario_1_capacity.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # after
        self.assertEqual(pool_0_name, pool_0.name)
        self.assertEqual(460, pool_0.free_capacity_gb)
        self.assertEqual(460, pool_0.virtual_free)
        self.assertEqual(40, pool_0.allocated_capacity_gb)
        self.assertEqual(40, pool_0.provisioned_capacity_gb)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_capacity_pool_notfound(self, m_cinder_helper):
        """test consuming capacity, new pool in existing node"""

        # storage_pool_by_name mock
        return_mock = mock.Mock()
        return_mock.configure_mock(
            name='host_0@backend_0#pool_2',
            total_volumes='2',
            total_capacity_gb='500',
            free_capacity_gb='380',
            provisioned_capacity_gb='120',
            allocated_capacity_gb='120')

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=lambda name: return_mock)

        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name)

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.CapacityNotificationEndpoint(self.fake_cdmc)

        message = self.load_message('scenario_1_capacity_pool_notfound.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # after consuming message, still pool_0 exists
        pool_0_name = 'host_0@backend_0#pool_0'
        pool_0 = storage_model.get_pool_by_pool_name(pool_0_name)
        self.assertEqual(pool_0_name, pool_0.name)
        self.assertEqual(420, pool_0.free_capacity_gb)
        self.assertEqual(420, pool_0.virtual_free)
        self.assertEqual(80, pool_0.allocated_capacity_gb)
        self.assertEqual(80, pool_0.provisioned_capacity_gb)

        # new pool was added
        pool_1_name = 'host_0@backend_0#pool_2'
        m_get_storage_pool_by_name.assert_called_once_with(pool_1_name)
        storage_node = storage_model.get_node_by_pool_name(pool_1_name)
        self.assertEqual('host_0@backend_0', storage_node.host)
        pool_1 = storage_model.get_pool_by_pool_name(pool_1_name)
        self.assertEqual(pool_1_name, pool_1.name)
        self.assertEqual(500, pool_1.total_capacity_gb)
        self.assertEqual(380, pool_1.free_capacity_gb)
        self.assertEqual(120, pool_1.allocated_capacity_gb)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_capacity_node_notfound(self, m_cinder_helper):
        """test consuming capacity, new pool in new node"""

        return_pool_mock = mock.Mock()
        return_pool_mock.configure_mock(
            name='host_2@backend_2#pool_0',
            total_volumes='2',
            total_capacity_gb='500',
            free_capacity_gb='460',
            provisioned_capacity_gb='40',
            allocated_capacity_gb='40')

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=lambda name: return_pool_mock)

        # storage_node_by_name mock
        return_node_mock = mock.Mock()
        return_node_mock.configure_mock(
            host='host_2@backend_2',
            zone='nova',
            state='up',
            status='enabled')

        m_get_storage_node_by_name = mock.Mock(
            side_effect=lambda name: return_node_mock)

        m_get_volume_type_by_backendname = mock.Mock(
            side_effect=lambda name: [mock.Mock('backend_2')])
        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name,
            get_storage_node_by_name=m_get_storage_node_by_name,
            get_volume_type_by_backendname=m_get_volume_type_by_backendname)

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.CapacityNotificationEndpoint(self.fake_cdmc)

        message = self.load_message('scenario_1_capacity_node_notfound.json')
        # self.assertRaises(exception.StorageNodeNotFound, handler.info,
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # new pool and new node was added
        node_1_name = 'host_2@backend_2'
        pool_1_name = node_1_name + '#pool_0'
        volume_type = 'backend_2'
        m_get_storage_pool_by_name.assert_called_once_with(pool_1_name)
        m_get_storage_node_by_name.assert_called_once_with(node_1_name)
        m_get_volume_type_by_backendname.assert_called_once_with(volume_type)
        # new node was added
        storage_node = storage_model.get_node_by_pool_name(pool_1_name)
        self.assertEqual('host_2@backend_2', storage_node.host)
        # new pool was added
        pool_1 = storage_model.get_pool_by_pool_name(pool_1_name)
        self.assertEqual(pool_1_name, pool_1.name)
        self.assertEqual(500, pool_1.total_capacity_gb)
        self.assertEqual(460, pool_1.free_capacity_gb)
        self.assertEqual(40, pool_1.allocated_capacity_gb)
        self.assertEqual(40, pool_1.provisioned_capacity_gb)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_volume_create(self, m_cinder_helper):
        """test creating volume in existing pool and node"""

        # create storage_pool_by_name mock
        return_pool_mock = mock.Mock()
        return_pool_mock.configure_mock(
            name='host_0@backend_0#pool_0',
            total_volumes='3',
            total_capacity_gb='500',
            free_capacity_gb='380',
            provisioned_capacity_gb='120',
            allocated_capacity_gb='120')

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=lambda name: return_pool_mock)

        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name)

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.VolumeCreateEnd(self.fake_cdmc)

        message = self.load_message('scenario_1_volume-create.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        # check that volume00 was added to the model
        volume_00_name = '990a723f-6c19-4f83-8526-6383c9e9389f'
        volume_00 = storage_model.get_volume_by_uuid(volume_00_name)
        self.assertEqual(volume_00_name, volume_00.uuid)
        self.assertFalse(volume_00.bootable)
        # check that capacity was updated
        pool_0_name = 'host_0@backend_0#pool_0'
        m_get_storage_pool_by_name.assert_called_once_with(pool_0_name)
        pool_0 = storage_model.get_pool_by_pool_name(pool_0_name)
        self.assertEqual(pool_0.name, pool_0_name)
        self.assertEqual(3, pool_0.total_volumes)
        self.assertEqual(380, pool_0.free_capacity_gb)
        self.assertEqual(120, pool_0.allocated_capacity_gb)
        self.assertEqual(120, pool_0.provisioned_capacity_gb)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_bootable_volume_create(self, m_cinder_helper):
        """test creating bootable volume in existing pool and node"""

        # create storage_pool_by_name mock
        return_pool_mock = mock.Mock()
        return_pool_mock.configure_mock(
            name='host_0@backend_0#pool_0',
            total_volumes='3',
            total_capacity_gb='500',
            free_capacity_gb='380',
            provisioned_capacity_gb='120',
            allocated_capacity_gb='120')

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=lambda name: return_pool_mock)

        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name)

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.VolumeCreateEnd(self.fake_cdmc)

        message = self.load_message('scenario_1_bootable-volume-create.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        # check that volume00 was added to the model
        volume_00_name = '990a723f-6c19-4f83-8526-6383c9e9389f'
        volume_00 = storage_model.get_volume_by_uuid(volume_00_name)
        self.assertEqual(volume_00_name, volume_00.uuid)
        self.assertTrue(volume_00.bootable)
        # check that capacity was updated
        pool_0_name = 'host_0@backend_0#pool_0'
        m_get_storage_pool_by_name.assert_called_once_with(pool_0_name)
        pool_0 = storage_model.get_pool_by_pool_name(pool_0_name)
        self.assertEqual(pool_0.name, pool_0_name)
        self.assertEqual(3, pool_0.total_volumes)
        self.assertEqual(380, pool_0.free_capacity_gb)
        self.assertEqual(120, pool_0.allocated_capacity_gb)
        self.assertEqual(120, pool_0.provisioned_capacity_gb)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_volume_create_pool_notfound(self, m_cinder_helper):
        """check creating volume in not existing pool and node"""

        # get_storage_pool_by_name mock
        return_pool_mock = mock.Mock()
        return_pool_mock.configure_mock(
            name='host_2@backend_2#pool_0',
            total_volumes='1',
            total_capacity_gb='500',
            free_capacity_gb='460',
            provisioned_capacity_gb='40',
            allocated_capacity_gb='40')

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=lambda name: return_pool_mock)

        # create storage_node_by_name mock
        return_node_mock = mock.Mock()
        return_node_mock.configure_mock(
            host='host_2@backend_2',
            zone='nova',
            state='up',
            status='enabled')

        m_get_storage_node_by_name = mock.Mock(
            side_effect=lambda name: return_node_mock)

        m_get_volume_type_by_backendname = mock.Mock(
            side_effect=lambda name: [mock.Mock('backend_2')])

        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name,
            get_storage_node_by_name=m_get_storage_node_by_name,
            get_volume_type_by_backendname=m_get_volume_type_by_backendname)

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.VolumeCreateEnd(self.fake_cdmc)

        message = self.load_message(
            'scenario_1_volume-create_pool_notfound.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        # check that volume00 was added to the model
        volume_00_name = '990a723f-6c19-4f83-8526-6383c9e9389f'
        volume_00 = storage_model.get_volume_by_uuid(volume_00_name)
        self.assertEqual(volume_00_name, volume_00.uuid)
        # check that capacity was updated
        node_2_name = 'host_2@backend_2'
        pool_0_name = node_2_name + '#pool_0'
        pool_0 = storage_model.get_pool_by_pool_name(pool_0_name)
        self.assertEqual(pool_0.name, pool_0_name)
        self.assertEqual(1, pool_0.total_volumes)
        self.assertEqual(460, pool_0.free_capacity_gb)
        self.assertEqual(40, pool_0.allocated_capacity_gb)
        self.assertEqual(40, pool_0.provisioned_capacity_gb)
        # check that node was added
        m_get_storage_node_by_name.assert_called_once_with(node_2_name)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_error_volume_unmapped(self, m_cinder_helper):
        """test creating error volume unmapped"""

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=exception.PoolNotFound(name="TEST"))
        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name)

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.VolumeCreateEnd(self.fake_cdmc)

        message = self.load_message('scenario_1_error-volume-create.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # we do not call get_storage_pool_by_name
        m_get_storage_pool_by_name.assert_not_called()
        # check that volume00 was added to the model
        volume_00_name = '990a723f-6c19-4f83-8526-6383c9e9389f'
        volume_00 = storage_model.get_volume_by_uuid(volume_00_name)
        self.assertEqual(volume_00_name, volume_00.uuid)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_volume_update(self, m_cinder_helper):
        """test updating volume in existing pool and node"""

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.VolumeUpdateEnd(self.fake_cdmc)

        volume_0_name = faker_cluster_state.volume_uuid_mapping['volume_0']
        volume_0 = storage_model.get_volume_by_uuid(volume_0_name)
        self.assertEqual('name_0', volume_0.name)

        # create storage_pool_by name mock
        return_pool_mock = mock.Mock()
        return_pool_mock.configure_mock(
            name='host_0@backend_0#pool_0',
            total_volumes='2',
            total_capacity_gb='500',
            free_capacity_gb='420',
            provisioned_capacity_gb='80',
            allocated_capacity_gb='80')

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=lambda name: return_pool_mock)

        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name)

        message = self.load_message('scenario_1_volume-update.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        # check that name of volume_0 was updated in the model
        volume_0 = storage_model.get_volume_by_uuid(volume_0_name)
        self.assertEqual('name_01', volume_0.name)

    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_volume_delete(self, m_cinder_helper):
        """test deleting volume"""

        # create storage_pool_by name mock
        return_pool_mock = mock.Mock()
        return_pool_mock.configure_mock(
            name='host_0@backend_0#pool_0',
            total_volumes='1',
            total_capacity_gb='500',
            free_capacity_gb='460',
            provisioned_capacity_gb='40',
            allocated_capacity_gb='40')

        m_get_storage_pool_by_name = mock.Mock(
            side_effect=lambda name: return_pool_mock)

        m_cinder_helper.return_value = mock.Mock(
            get_storage_pool_by_name=m_get_storage_pool_by_name)

        storage_model = self.fake_cdmc.generate_scenario_1()
        self.fake_cdmc.cluster_data_model = storage_model
        handler = cnotification.VolumeDeleteEnd(self.fake_cdmc)

        # volume exists before consuming
        volume_0_uuid = faker_cluster_state.volume_uuid_mapping['volume_0']
        volume_0 = storage_model.get_volume_by_uuid(volume_0_uuid)
        self.assertEqual(volume_0_uuid, volume_0.uuid)

        message = self.load_message('scenario_1_volume-delete.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # volume does not exists after consuming
        self.assertRaises(
            exception.VolumeNotFound,
            storage_model.get_volume_by_uuid, volume_0_uuid)

        # check that capacity was updated
        pool_0_name = 'host_0@backend_0#pool_0'
        m_get_storage_pool_by_name.assert_called_once_with(pool_0_name)
        pool_0 = storage_model.get_pool_by_pool_name(pool_0_name)
        self.assertEqual(pool_0.name, pool_0_name)
        self.assertEqual(1, pool_0.total_volumes)
        self.assertEqual(460, pool_0.free_capacity_gb)
        self.assertEqual(40, pool_0.allocated_capacity_gb)
        self.assertEqual(40, pool_0.provisioned_capacity_gb)
