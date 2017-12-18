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
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import service as watcher_service
from watcher.decision_engine.model import element
from watcher.decision_engine.model.notification import nova as novanotification
from watcher.tests import base as base_test
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


class TestReceiveNovaNotifications(NotificationTestCase):

    FAKE_METADATA = {'message_id': None, 'timestamp': None}

    def setUp(self):
        super(TestReceiveNovaNotifications, self).setUp()

        p_from_dict = mock.patch.object(context.RequestContext, 'from_dict')
        m_from_dict = p_from_dict.start()
        m_from_dict.return_value = self.context
        self.addCleanup(p_from_dict.stop)
        p_heartbeat = mock.patch.object(
            watcher_service.ServiceHeartbeat, "send_beat")
        self.m_heartbeat = p_heartbeat.start()
        self.addCleanup(p_heartbeat.stop)

    @mock.patch.object(novanotification.ServiceUpdated, 'info')
    def test_nova_receive_service_update(self, m_info):
        message = self.load_message('service-update.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'nova-compute:host1', 'service.update',
            expected_message, self.FAKE_METADATA)

    @mock.patch.object(novanotification.InstanceCreated, 'info')
    def test_nova_receive_instance_create(self, m_info):
        message = self.load_message('instance-create.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'nova-compute:compute', 'instance.update',
            expected_message, self.FAKE_METADATA)

    @mock.patch.object(novanotification.InstanceUpdated, 'info')
    def test_nova_receive_instance_update(self, m_info):
        message = self.load_message('instance-update.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'nova-compute:compute', 'instance.update',
            expected_message, self.FAKE_METADATA)

    @mock.patch.object(novanotification.InstanceDeletedEnd, 'info')
    def test_nova_receive_instance_delete_end(self, m_info):
        message = self.load_message('instance-delete-end.json')
        expected_message = message['payload']

        de_service = watcher_service.Service(fake_managers.FakeManager)
        incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

        de_service.notification_handler.dispatcher.dispatch(incoming)
        m_info.assert_called_once_with(
            self.context, 'nova-compute:compute', 'instance.delete.end',
            expected_message, self.FAKE_METADATA)


class TestNovaNotifications(NotificationTestCase):

    FAKE_METADATA = {'message_id': None, 'timestamp': None}

    def setUp(self):
        super(TestNovaNotifications, self).setUp()
        # fake cluster
        self.fake_cdmc = faker_cluster_state.FakerModelCollector()

    def test_nova_service_update(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.ServiceUpdated(self.fake_cdmc)

        node0_uuid = 'Node_0'
        node0 = compute_model.get_node_by_uuid(node0_uuid)

        message = self.load_message('scenario3_service-update-disabled.json')

        self.assertEqual('hostname_0', node0.hostname)
        self.assertEqual(element.ServiceState.ONLINE.value, node0.state)
        self.assertEqual(element.ServiceState.ENABLED.value, node0.status)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual('Node_0', node0.hostname)
        self.assertEqual(element.ServiceState.OFFLINE.value, node0.state)
        self.assertEqual(element.ServiceState.DISABLED.value, node0.status)

        message = self.load_message('scenario3_service-update-enabled.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual('Node_0', node0.hostname)
        self.assertEqual(element.ServiceState.ONLINE.value, node0.state)
        self.assertEqual(element.ServiceState.ENABLED.value, node0.status)

    def test_nova_instance_update(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.InstanceUpdated(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('scenario3_instance-update.json')

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)

    @mock.patch.object(nova_helper, "NovaHelper")
    def test_nova_instance_update_notfound_still_creates(
            self, m_nova_helper_cls):
        m_get_compute_node_by_hostname = mock.Mock(
            side_effect=lambda uuid: mock.Mock(
                name='m_get_compute_node_by_hostname',
                id=3,
                hypervisor_hostname="Node_2",
                state='up',
                status='enabled',
                uuid=uuid,
                memory_mb=7777,
                vcpus=42,
                free_disk_gb=974,
                local_gb=1337))
        m_nova_helper_cls.return_value = mock.Mock(
            get_compute_node_by_hostname=m_get_compute_node_by_hostname,
            name='m_nova_helper')
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.InstanceUpdated(self.fake_cdmc)

        instance0_uuid = '9966d6bd-a45c-4e1c-9d57-3054899a3ec7'

        message = self.load_message('scenario3_notfound_instance-update.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)
        self.assertEqual(1, instance0.vcpus)
        self.assertEqual(1, instance0.disk_capacity)
        self.assertEqual(512, instance0.memory)

        m_get_compute_node_by_hostname.assert_called_once_with('Node_2')
        node_2 = compute_model.get_node_by_uuid('Node_2')
        self.assertEqual(7777, node_2.memory)
        self.assertEqual(42, node_2.vcpus)
        self.assertEqual(974, node_2.disk)
        self.assertEqual(1337, node_2.disk_capacity)

    @mock.patch.object(nova_helper, "NovaHelper")
    def test_instance_update_node_notfound_set_unmapped(
            self, m_nova_helper_cls):
        m_get_compute_node_by_hostname = mock.Mock(
            side_effect=exception.ComputeNodeNotFound(name="TEST"))
        m_nova_helper_cls.return_value = mock.Mock(
            get_compute_node_by_hostname=m_get_compute_node_by_hostname,
            name='m_nova_helper')

        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.InstanceUpdated(self.fake_cdmc)

        instance0_uuid = '9966d6bd-a45c-4e1c-9d57-3054899a3ec7'

        message = self.load_message(
            'scenario3_notfound_instance-update.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)
        self.assertEqual(1, instance0.vcpus)
        self.assertEqual(1, instance0.disk)
        self.assertEqual(1, instance0.disk_capacity)
        self.assertEqual(512, instance0.memory)

        m_get_compute_node_by_hostname.assert_any_call('Node_2')
        self.assertRaises(
            exception.ComputeNodeNotFound,
            compute_model.get_node_by_uuid, 'Node_2')

    def test_nova_instance_create(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.InstanceCreated(self.fake_cdmc)

        instance0_uuid = 'c03c0bf9-f46e-4e4f-93f1-817568567ee2'

        self.assertRaises(
            exception.InstanceNotFound,
            compute_model.get_instance_by_uuid, instance0_uuid)

        message = self.load_message('scenario3_instance-create.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)
        self.assertEqual(1, instance0.vcpus)
        self.assertEqual(1, instance0.disk_capacity)
        self.assertEqual(512, instance0.memory)

    def test_nova_instance_delete_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.InstanceDeletedEnd(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'

        # Before
        self.assertTrue(compute_model.get_instance_by_uuid(instance0_uuid))

        message = self.load_message('scenario3_instance-delete-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # After
        self.assertRaises(
            exception.InstanceNotFound,
            compute_model.get_instance_by_uuid, instance0_uuid)


class TestLegacyNovaNotifications(NotificationTestCase):

    FAKE_METADATA = {'message_id': None, 'timestamp': None}

    def setUp(self):
        super(TestLegacyNovaNotifications, self).setUp()
        # fake cluster
        self.fake_cdmc = faker_cluster_state.FakerModelCollector()

    def test_legacy_instance_created_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyInstanceCreatedEnd(self.fake_cdmc)

        instance0_uuid = 'c03c0bf9-f46e-4e4f-93f1-817568567ee2'
        self.assertRaises(
            exception.InstanceNotFound,
            compute_model.get_instance_by_uuid, instance0_uuid)

        message = self.load_message(
            'scenario3_legacy_instance-create-end.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)
        self.assertEqual(1, instance0.vcpus)
        self.assertEqual(1, instance0.disk_capacity)
        self.assertEqual(512, instance0.memory)

    def test_legacy_instance_updated(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyInstanceUpdated(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('scenario3_legacy_instance-update.json')

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)

    @mock.patch.object(nova_helper, "NovaHelper")
    def test_legacy_instance_update_node_notfound_still_creates(
            self, m_nova_helper_cls):
        m_get_compute_node_by_hostname = mock.Mock(
            side_effect=lambda uuid: mock.Mock(
                name='m_get_compute_node_by_hostname',
                id=3,
                uuid=uuid,
                hypervisor_hostname="Node_2",
                state='up',
                status='enabled',
                memory_mb=7777,
                vcpus=42,
                free_disk_gb=974,
                local_gb=1337))
        m_nova_helper_cls.return_value = mock.Mock(
            get_compute_node_by_hostname=m_get_compute_node_by_hostname,
            name='m_nova_helper')

        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyInstanceUpdated(self.fake_cdmc)

        instance0_uuid = '9966d6bd-a45c-4e1c-9d57-3054899a3ec7'

        message = self.load_message(
            'scenario3_notfound_legacy_instance-update.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)
        self.assertEqual(1, instance0.vcpus)
        self.assertEqual(1, instance0.disk)
        self.assertEqual(1, instance0.disk_capacity)
        self.assertEqual(512, instance0.memory)

        m_get_compute_node_by_hostname.assert_any_call('Node_2')
        node_2 = compute_model.get_node_by_uuid('Node_2')
        self.assertEqual(7777, node_2.memory)
        self.assertEqual(42, node_2.vcpus)
        self.assertEqual(974, node_2.disk)
        self.assertEqual(1337, node_2.disk_capacity)

    @mock.patch.object(nova_helper, "NovaHelper")
    def test_legacy_instance_update_node_notfound_set_unmapped(
            self, m_nova_helper_cls):
        m_get_compute_node_by_hostname = mock.Mock(
            side_effect=exception.ComputeNodeNotFound)
        m_nova_helper_cls.return_value = mock.Mock(
            get_compute_node_by_hostname=m_get_compute_node_by_hostname,
            name='m_nova_helper')

        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyInstanceUpdated(self.fake_cdmc)

        instance0_uuid = '9966d6bd-a45c-4e1c-9d57-3054899a3ec7'

        message = self.load_message(
            'scenario3_notfound_legacy_instance-update.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)
        self.assertEqual(1, instance0.vcpus)
        self.assertEqual(1, instance0.disk)
        self.assertEqual(1, instance0.disk_capacity)
        self.assertEqual(512, instance0.memory)

        m_get_compute_node_by_hostname.assert_any_call('Node_2')
        self.assertRaises(
            exception.ComputeNodeNotFound,
            compute_model.get_node_by_uuid, 'Node_2')

    def test_legacy_live_migrated_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyLiveMigratedEnd(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('Node_0', node.uuid)

        message = self.load_message(
            'scenario3_legacy_livemigration-post-dest-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('Node_1', node.uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_legacy_instance_deleted_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyInstanceDeletedEnd(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'

        # Before
        self.assertTrue(compute_model.get_instance_by_uuid(instance0_uuid))

        message = self.load_message(
            'scenario3_legacy_instance-delete-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # After
        self.assertRaises(
            exception.InstanceNotFound,
            compute_model.get_instance_by_uuid, instance0_uuid)

    def test_legacy_instance_resize_confirm_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyLiveMigratedEnd(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('Node_0', node.uuid)

        message = self.load_message(
            'scenario3_legacy_instance-resize-confirm-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('Node_1', node.uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_legacy_instance_rebuild_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.LegacyLiveMigratedEnd(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('Node_0', node.uuid)

        message = self.load_message(
            'scenario3_legacy_instance-rebuild-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('Node_1', node.uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)
