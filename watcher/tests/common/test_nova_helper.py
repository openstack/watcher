# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

import time

import mock

from watcher.common import clients
from watcher.common import nova_helper
from watcher.common import utils
from watcher.tests import base


@mock.patch.object(clients.OpenStackClients, 'nova')
@mock.patch.object(clients.OpenStackClients, 'neutron')
@mock.patch.object(clients.OpenStackClients, 'cinder')
@mock.patch.object(clients.OpenStackClients, 'glance')
class TestNovaHelper(base.TestCase):

    def setUp(self):
        super(TestNovaHelper, self).setUp()
        self.instance_uuid = "fb5311b7-37f3-457e-9cde-6494a3c59bfe"
        self.source_node = "ldev-indeedsrv005"
        self.destination_node = "ldev-indeedsrv006"
        self.flavor_name = "x1"

    @staticmethod
    def fake_server(*args, **kwargs):
        server = mock.MagicMock()
        server.id = args[0]
        server.status = 'ACTIVE'

        return server

    @staticmethod
    def fake_migration(*args, **kwargs):
        migration = mock.MagicMock()
        migration.id = args[0]
        return migration

    @staticmethod
    def fake_nova_find_list(nova_util, find=None, list=None):
        nova_util.nova.servers.get.return_value = find
        if list is None:
            nova_util.nova.servers.list.return_value = []
        else:
            nova_util.nova.servers.list.return_value = [list]

    @staticmethod
    def fake_nova_migration_list(nova_util, list=None):
        if list is None:
            nova_util.nova.server_migrations.list.return_value = []
        else:
            nova_util.nova.server_migration.list.return_value = [list]

    @staticmethod
    def fake_live_migrate(server, *args, **kwargs):

        def side_effect(*args, **kwargs):
            setattr(server, 'OS-EXT-SRV-ATTR:host', "compute-2")

        server.live_migrate.side_effect = side_effect

    @staticmethod
    def fake_confirm_resize(server, *args, **kwargs):

        def side_effect(*args, **kwargs):
            setattr(server, 'status', 'ACTIVE')

        server.confirm_resize.side_effect = side_effect

    @staticmethod
    def fake_cold_migrate(server, *args, **kwargs):

        def side_effect(*args, **kwargs):
            setattr(server, 'OS-EXT-SRV-ATTR:host', "compute-2")
            setattr(server, 'status', 'VERIFY_RESIZE')

        server.migrate.side_effect = side_effect

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_stop_instance(self, mock_glance, mock_cinder, mock_neutron,
                           mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        server = self.fake_server(instance_id)
        setattr(server, 'OS-EXT-STS:vm_state', 'stopped')
        self.fake_nova_find_list(nova_util, find=server, list=server)

        result = nova_util.stop_instance(instance_id)
        self.assertTrue(result)

        setattr(server, 'OS-EXT-STS:vm_state', 'active')
        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

        self.fake_nova_find_list(nova_util, find=server, list=None)

        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

    def test_set_host_offline(self, mock_glance, mock_cinder, mock_neutron,
                              mock_nova):
        host = mock.MagicMock()
        nova_util = nova_helper.NovaHelper()
        nova_util.nova.hosts = mock.MagicMock()
        nova_util.nova.hosts.get.return_value = host
        result = nova_util.set_host_offline("rennes")
        self.assertTrue(result)

        nova_util.nova.hosts.get.return_value = None
        result = nova_util.set_host_offline("rennes")
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_resize_instance(self, mock_glance, mock_cinder,
                             mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'status', 'VERIFY_RESIZE')
        self.fake_nova_find_list(nova_util, find=server, list=server)
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertTrue(is_success)

        setattr(server, 'status', 'SOMETHING_ELSE')
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertFalse(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_live_migrate_instance(self, mock_glance, mock_cinder,
                                   mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.destination_node)
        self.fake_nova_find_list(nova_util, find=server, list=server)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.source_node)
        self.fake_nova_find_list(nova_util, find=server, list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_live_migrate_instance_with_task_state(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.source_node)
        setattr(server, 'OS-EXT-STS:task_state', '')
        self.fake_nova_find_list(nova_util, find=server, list=None)
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        time.sleep.assert_not_called()

        setattr(server, 'OS-EXT-STS:task_state', 'migrating')
        self.fake_nova_find_list(nova_util, find=server, list=server)
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        time.sleep.assert_called_with(1)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_live_migrate_instance_no_destination_node(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        self.destination_node = None
        self.fake_nova_find_list(nova_util, find=server, list=server)
        self.fake_live_migrate(server)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

    def test_watcher_non_live_migrate_instance_not_found(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        self.fake_nova_find_list(nova_util, find=None, list=None)

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node)

        self.assertFalse(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_watcher_non_live_migrate_instance_volume(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_servers = nova_util.nova.servers
        instance = self.fake_server(self.instance_uuid)
        setattr(instance, 'OS-EXT-SRV-ATTR:host',
                          self.source_node)
        setattr(instance, 'OS-EXT-STS:vm_state', "stopped")
        attached_volumes = [{'id': str(utils.generate_uuid())}]
        setattr(instance, "os-extended-volumes:volumes_attached",
                attached_volumes)
        self.fake_nova_find_list(nova_util, find=instance, list=instance)
        nova_servers.create_image.return_value = utils.generate_uuid()
        nova_util.glance.images.get.return_value = mock.MagicMock(
            status='active')
        nova_util.cinder.volumes.get.return_value = mock.MagicMock(
            status='available')

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node)
        self.assertTrue(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_watcher_non_live_migrate_keep_image(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_servers = nova_util.nova.servers
        instance = self.fake_server(self.instance_uuid)
        setattr(instance, 'OS-EXT-SRV-ATTR:host',
                self.source_node)
        setattr(instance, 'OS-EXT-STS:vm_state', "stopped")
        addresses = mock.MagicMock()
        network_type = mock.MagicMock()
        networks = []
        networks.append(("lan", network_type))
        addresses.items.return_value = networks
        attached_volumes = mock.MagicMock()
        setattr(instance, 'addresses', addresses)
        setattr(instance, "os-extended-volumes:volumes_attached",
                attached_volumes)
        self.fake_nova_find_list(nova_util, find=instance, list=instance)
        nova_servers.create_image.return_value = utils.generate_uuid()
        nova_util.glance.images.get.return_value = mock.MagicMock(
            status='active')
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node, keep_original_image_name=False)
        self.assertTrue(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_abort_live_migrate_instance(self, mock_glance, mock_cinder,
                                         mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.source_node)
        setattr(server, 'OS-EXT-STS:task_state', None)
        migration = self.fake_migration(2)
        self.fake_nova_migration_list(nova_util, list=migration)

        self.fake_nova_find_list(nova_util, find=server, list=server)

        self.assertTrue(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        setattr(server, 'OS-EXT-SRV-ATTR:host', self.destination_node)

        self.assertFalse(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        setattr(server, 'status', 'ERROR')
        self.assertRaises(Exception, nova_util.abort_live_migrate,
                          (self.instance_uuid, self.source_node,
                           self.destination_node))

    def test_non_live_migrate_instance_no_destination_node(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                self.source_node)
        self.destination_node = None
        self.fake_nova_find_list(nova_util, find=server, list=server)
        self.fake_cold_migrate(server)
        self.fake_confirm_resize(server)
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_create_image_from_instance(self, mock_glance, mock_cinder,
                                        mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        image = mock.MagicMock()
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_node)
        setattr(instance, 'OS-EXT-STS:vm_state', "stopped")
        self.fake_nova_find_list(nova_util, find=instance, list=instance)
        image_uuid = 'fake-image-uuid'
        nova_util.nova.servers.create_image.return_value = image

        glance_client = mock.MagicMock()
        mock_glance.return_value = glance_client

        glance_client.images = {image_uuid: image}
        instance = nova_util.create_image_from_instance(
            self.instance_uuid, "Cirros"
        )
        self.assertIsNotNone(instance)

        nova_util.glance.images.get.return_value = None
        instance = nova_util.create_image_from_instance(
            self.instance_uuid, "Cirros"
        )
        self.assertIsNone(instance)

    def test_enable_service_nova_compute(self, mock_glance, mock_cinder,
                                         mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_services = nova_util.nova.services
        nova_services.enable.return_value = mock.MagicMock(
            status='enabled')

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertTrue(result)

        nova_services.enable.return_value = mock.MagicMock(
            status='disabled')

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertFalse(result)

    def test_disable_service_nova_compute(self, mock_glance, mock_cinder,
                                          mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_services = nova_util.nova.services
        nova_services.disable_log_reason.return_value = mock.MagicMock(
            status='enabled')

        result = nova_util.disable_service_nova_compute('nanjing')
        self.assertFalse(result)

        nova_services.disable_log_reason.return_value = mock.MagicMock(
            status='disabled')

        result = nova_util.disable_service_nova_compute('nanjing')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_create_instance(self, mock_glance, mock_cinder,
                             mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        nova_util.nova.services.create.return_value = instance
        nova_util.nova.services.get.return_value = instance

        instance = nova_util.create_instance(self.source_node)
        self.assertIsNotNone(instance)

    def test_get_flavor_instance(self, mock_glance, mock_cinder,
                                 mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        flavor = {'id': 1, 'name': 'm1.tiny', 'ram': 512, 'vcpus': 1,
                  'disk': 0, 'ephemeral': 0}
        instance.flavor = flavor
        nova_util.nova.flavors.get.return_value = flavor
        cache = flavor

        nova_util.get_flavor_instance(instance, cache)
        self.assertEqual(instance.flavor['name'], cache['name'])

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock()
        volume.id = kwargs.get('id', '45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba')
        volume.size = kwargs.get('size', '1')
        volume.status = kwargs.get('status', 'available')
        volume.snapshot_id = kwargs.get('snapshot_id', None)
        volume.availability_zone = kwargs.get('availability_zone', 'nova')
        return volume

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_swap_volume(self, mock_glance, mock_cinder,
                         mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, find=server, list=server)

        old_volume = self.fake_volume(
            status='in-use', attachments=[{'server_id': self.instance_uuid}])
        new_volume = self.fake_volume(
            id=utils.generate_uuid(), status='in-use')

        result = nova_util.swap_volume(old_volume, new_volume)
        self.assertTrue(result)
