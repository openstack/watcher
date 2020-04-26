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
import os_resource_classes as orc
from unittest import mock

from oslo_serialization import jsonutils

from watcher.common import context
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import placement_helper
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
    FAKE_NOTIFICATIONS = {
        'instance.create.end': 'instance-create-end.json',
        'instance.lock': 'instance-lock.json',
        'instance.unlock': 'instance-unlock.json',
        'instance.pause.end': 'instance-pause-end.json',
        'instance.power_off.end': 'instance-power_off-end.json',
        'instance.power_on.end': 'instance-power_on-end.json',
        'instance.resize_confirm.end': 'instance-resize_confirm-end.json',
        'instance.restore.end': 'instance-restore-end.json',
        'instance.resume.end': 'instance-resume-end.json',
        'instance.shelve.end': 'instance-shelve-end.json',
        'instance.shutdown.end': 'instance-shutdown-end.json',
        'instance.suspend.end': 'instance-suspend-end.json',
        'instance.unpause.end': 'instance-unpause-end.json',
        'instance.unrescue.end': 'instance-unrescue-end.json',
        'instance.unshelve.end': 'instance-unshelve-end.json',
        'instance.rebuild.end': 'instance-rebuild-end.json',
        'instance.rescue.end': 'instance-rescue-end.json',
        'instance.update': 'instance-update.json',
        'instance.live_migration_force_complete.end':
        'instance-live_migration_force_complete-end.json',
        'instance.live_migration_post.end':
        'instance-live_migration_post-end.json',
        'instance.delete.end': 'instance-delete-end.json',
        'instance.soft_delete.end': 'instance-soft_delete-end.json',
        'service.create': 'service-create.json',
        'service.delete': 'service-delete.json',
        'service.update': 'service-update.json',
        }

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

    @mock.patch.object(novanotification.VersionedNotification, 'info')
    def test_receive_nova_notifications(self, m_info):
        de_service = watcher_service.Service(fake_managers.FakeManager)
        n_dicts = novanotification.VersionedNotification.notification_mapping
        for n_type in n_dicts.keys():
            n_json = self.FAKE_NOTIFICATIONS[n_type]
            message = self.load_message(n_json)
            expected_message = message['payload']
            publisher_id = message['publisher_id']

            incoming = mock.Mock(ctxt=self.context.to_dict(), message=message)

            de_service.notification_handler.dispatcher.dispatch(incoming)
            m_info.assert_called_with(
                self.context, publisher_id, n_type,
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
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        node0_name = "hostname_0"
        node0 = compute_model.get_node_by_name(node0_name)

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

        self.assertEqual("hostname_0", node0.hostname)
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

        self.assertEqual("hostname_0", node0.hostname)
        self.assertEqual(element.ServiceState.ONLINE.value, node0.state)
        self.assertEqual(element.ServiceState.ENABLED.value, node0.status)

    @mock.patch.object(placement_helper, 'PlacementHelper')
    @mock.patch.object(nova_helper, "NovaHelper")
    def test_nova_service_create(self, m_nova_helper_cls,
                                 m_placement_helper):
        mock_placement = mock.Mock(name="placement_helper")
        mock_placement.get_inventories.return_value = dict()
        mock_placement.get_usages_for_resource_provider.return_value = {
            orc.DISK_GB: 10,
            orc.MEMORY_MB: 100,
            orc.VCPU: 0
        }
        m_placement_helper.return_value = mock_placement
        m_get_compute_node_by_hostname = mock.Mock(
            side_effect=lambda uuid: mock.Mock(
                name='m_get_compute_node_by_uuid',
                id="fafac544-906b-4a6a-a9c6-c1f7a8078c73",
                hypervisor_hostname="host2",
                state='up',
                status='enabled',
                memory_mb=7777,
                vcpus=42,
                free_disk_gb=974,
                local_gb=1337,
                service={'id': 123, 'host': 'host2',
                         'disabled_reason': ''},))
        m_nova_helper_cls.return_value = mock.Mock(
            get_compute_node_by_hostname=m_get_compute_node_by_hostname,
            name='m_nova_helper')

        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        new_node_name = "host2"

        self.assertRaises(
            exception.ComputeNodeNotFound,
            compute_model.get_node_by_name, new_node_name)

        message = self.load_message('service-create.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        new_node = compute_model.get_node_by_name(new_node_name)
        self.assertEqual('host2', new_node.hostname)
        self.assertEqual(element.ServiceState.ONLINE.value, new_node.state)
        self.assertEqual(element.ServiceState.ENABLED.value, new_node.status)

    def test_nova_service_delete(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        node0_name = "hostname_0"

        # Before
        self.assertTrue(compute_model.get_node_by_name(node0_name))

        message = self.load_message('service-delete.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # After
        self.assertRaises(
            exception.ComputeNodeNotFound,
            compute_model.get_node_by_name, node0_name)

    def test_nova_instance_update(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-update.json')

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)

    def test_nova_instance_state_building(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        message = self.load_message('instance-update.json')

        message['payload']['nova_object.data']['state'] = 'building'

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        # Assert that the instance state in the model is unchanged
        # since the 'building' state is ignored.
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    @mock.patch.object(placement_helper, 'PlacementHelper')
    @mock.patch.object(nova_helper, "NovaHelper")
    def test_nova_instance_update_notfound_still_creates(
            self, m_nova_helper_cls, m_placement_helper):
        mock_placement = mock.Mock(name="placement_helper")
        mock_placement.get_inventories.return_value = dict()
        mock_placement.get_usages_for_resource_provider.return_value = {
            orc.DISK_GB: 10,
            orc.MEMORY_MB: 100,
            orc.VCPU: 0
        }
        m_placement_helper.return_value = mock_placement
        m_get_compute_node_by_hostname = mock.Mock(
            side_effect=lambda uuid: mock.Mock(
                name='m_get_compute_node_by_hostname',
                id='669966bd-a45c-4e1c-9d57-3054899a3ec7',
                hypervisor_hostname="Node_2",
                state='up',
                status='enabled',
                memory_mb=7777,
                vcpus=42,
                free_disk_gb=974,
                local_gb=1337,
                service={'id': 123, 'host': 'Node_2',
                         'disabled_reason': ''},))
        m_nova_helper_cls.return_value = mock.Mock(
            get_compute_node_by_hostname=m_get_compute_node_by_hostname,
            name='m_nova_helper')
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

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
        self.assertEqual(1, instance0.disk)
        self.assertEqual(512, instance0.memory)

        m_get_compute_node_by_hostname.assert_called_once_with('Node_2')
        node_2 = compute_model.get_node_by_name('Node_2')
        self.assertEqual(7777, node_2.memory)
        self.assertEqual(42, node_2.vcpus)
        self.assertEqual(1337, node_2.disk)

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
        handler = novanotification.VersionedNotification(self.fake_cdmc)

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
        self.assertEqual(512, instance0.memory)

        m_get_compute_node_by_hostname.assert_any_call('Node_2')
        self.assertRaises(
            exception.ComputeNodeNotFound,
            compute_model.get_node_by_uuid, 'Node_2')

    @mock.patch.object(placement_helper, 'PlacementHelper')
    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_nova_instance_create(self, m_nova_helper_cls,
                                  m_placement_helper):
        mock_placement = mock.Mock(name="placement_helper")
        mock_placement.get_inventories.return_value = dict()
        mock_placement.get_usages_for_resource_provider.return_value = {
            orc.DISK_GB: 10,
            orc.MEMORY_MB: 100,
            orc.VCPU: 0
        }
        m_placement_helper.return_value = mock_placement
        m_get_compute_node_by_hostname = mock.Mock(
            side_effect=lambda uuid: mock.Mock(
                name='m_get_compute_node_by_hostname',
                id=3,
                hypervisor_hostname="compute",
                state='up',
                status='enabled',
                uuid=uuid,
                memory_mb=7777,
                vcpus=42,
                free_disk_gb=974,
                local_gb=1337,
                service={'id': 123, 'host': 'compute',
                         'disabled_reason': ''},))
        m_nova_helper_cls.return_value = mock.Mock(
            get_compute_node_by_hostname=m_get_compute_node_by_hostname,
            name='m_nova_helper')

        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = 'c03c0bf9-f46e-4e4f-93f1-817568567ee2'

        self.assertRaises(
            exception.InstanceNotFound,
            compute_model.get_instance_by_uuid, instance0_uuid)

        message = self.load_message('instance-create-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        hostname = message['payload']['nova_object.data']['host']
        node = self.fake_cdmc.cluster_data_model.get_node_by_instance_uuid(
            instance0_uuid)
        self.assertEqual(hostname, node.hostname)
        m_get_compute_node_by_hostname.assert_called_once_with(hostname)

        instance0 = self.fake_cdmc.cluster_data_model.get_instance_by_uuid(
            instance0_uuid)

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)
        self.assertEqual(1, instance0.vcpus)
        self.assertEqual(1, instance0.disk)
        self.assertEqual(512, instance0.memory)

    def test_nova_instance_delete_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'

        # Before
        self.assertTrue(compute_model.get_instance_by_uuid(instance0_uuid))

        message = self.load_message('instance-delete-end.json')
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

    def test_nova_instance_soft_delete_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'

        # Before
        self.assertTrue(compute_model.get_instance_by_uuid(instance0_uuid))

        message = self.load_message('instance-soft_delete-end.json')
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

    def test_live_migrated_force_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)
        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('fa69c544-906b-4a6a-a9c6-c1f7a8078c73', node.uuid)
        message = self.load_message(
            'instance-live_migration_force_complete-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('fa69c544-906b-4a6a-a9c6-c1f7a8078c73', node.uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_live_migrated_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)
        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('fa69c544-906b-4a6a-a9c6-c1f7a8078c73', node.uuid)
        message = self.load_message(
            'instance-live_migration_post-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('fa69c544-906b-4a6a-a9c6-c1f7a8078c73', node.uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_nova_instance_lock(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-lock.json')

        self.assertFalse(instance0.locked)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertTrue(instance0.locked)

        message = self.load_message('instance-unlock.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertFalse(instance0.locked)

    def test_nova_instance_pause(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-pause-end.json')

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.PAUSED.value, instance0.state)

        message = self.load_message('instance-unpause-end.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_nova_instance_power_on_off(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-power_off-end.json')

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.STOPPED.value, instance0.state)

        message = self.load_message('instance-power_on-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_instance_rebuild_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)
        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual("fa69c544-906b-4a6a-a9c6-c1f7a8078c73", node.uuid)
        message = self.load_message('instance-rebuild-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('hostname_0', node.hostname)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_nova_instance_rescue(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-rescue-end.json')

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.RESCUED.value, instance0.state)

        message = self.load_message('instance-unrescue-end.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_instance_resize_confirm_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)
        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('fa69c544-906b-4a6a-a9c6-c1f7a8078c73', node.uuid)
        message = self.load_message(
            'instance-resize_confirm-end.json')
        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )
        node = compute_model.get_node_by_instance_uuid(instance0_uuid)
        self.assertEqual('fa69c544-906b-4a6a-a9c6-c1f7a8078c73', node.uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_nova_instance_restore_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-restore-end.json')
        instance0.state = element.InstanceState.ERROR.value
        self.assertEqual(element.InstanceState.ERROR.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_nova_instance_resume_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-resume-end.json')
        instance0.state = element.InstanceState.ERROR.value
        self.assertEqual(element.InstanceState.ERROR.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_nova_instance_shelve(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-shelve-end.json')
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.SHELVED.value, instance0.state)

        message = self.load_message('instance-unshelve-end.json')

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

    def test_nova_instance_shutdown_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-shutdown-end.json')
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(element.InstanceState.STOPPED.value, instance0.state)

    def test_nova_instance_suspend_end(self):
        compute_model = self.fake_cdmc.generate_scenario_3_with_2_nodes()
        self.fake_cdmc.cluster_data_model = compute_model
        handler = novanotification.VersionedNotification(self.fake_cdmc)

        instance0_uuid = '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        instance0 = compute_model.get_instance_by_uuid(instance0_uuid)

        message = self.load_message('instance-suspend-end.json')
        self.assertEqual(element.InstanceState.ACTIVE.value, instance0.state)

        handler.info(
            ctxt=self.context,
            publisher_id=message['publisher_id'],
            event_type=message['event_type'],
            payload=message['payload'],
            metadata=self.FAKE_METADATA,
        )

        self.assertEqual(
            element.InstanceState.SUSPENDED.value, instance0.state)

    def test_info_no_cdm(self):
        # Tests that a notification is received before an audit has been
        # performed which would create the nova CDM.
        mock_collector = mock.Mock(cluster_data_model=None)
        handler = novanotification.VersionedNotification(mock_collector)
        payload = {
            'nova_object.data': {
                'uuid': '9966d6bd-a45c-4e1c-9d57-3054899a3ec7',
                'host': None
            }
        }
        with mock.patch.object(handler, 'update_instance') as update_instance:
            handler.info(mock.sentinel.ctxt, 'publisher_id', 'instance.update',
                         payload, metadata={})
            # update_instance should not be called since we did not add an
            # Instance object to the CDM since the CDM does not exist yet.
            update_instance.assert_not_called()

    def test_fake_instance_create(self):
        self.fake_cdmc.cluster_data_model = mock.Mock()
        handler = novanotification.VersionedNotification(self.fake_cdmc)
        message = self.load_message('instance-create-end.json')

        # get_instance_by_uuid should not be called when creating instance
        with mock.patch.object(self.fake_cdmc.cluster_data_model,
                               'get_instance_by_uuid') as mock_get:
            handler.info(
                ctxt=self.context,
                publisher_id=message['publisher_id'],
                event_type=message['event_type'],
                payload=message['payload'],
                metadata=self.FAKE_METADATA,
            )
            mock_get.assert_not_called()
