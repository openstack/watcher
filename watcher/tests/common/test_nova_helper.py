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
        self.source_hypervisor = "ldev-indeedsrv005"
        self.destination_hypervisor = "ldev-indeedsrv006"

    def test_stop_instance(self, mock_glance, mock_cinder, mock_neutron,
                           mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        server = mock.MagicMock()
        server.id = instance_id
        setattr(server, 'OS-EXT-STS:vm_state', 'stopped')
        nova_util.nova.servers = mock.MagicMock()
        nova_util.nova.servers.find.return_value = server
        nova_util.nova.servers.list.return_value = [server]

        result = nova_util.stop_instance(instance_id)
        self.assertEqual(True, result)

    def test_set_host_offline(self, mock_glance, mock_cinder, mock_neutron,
                              mock_nova):
        nova_util = nova_helper.NovaHelper()
        host = mock.MagicMock()
        nova_util.nova.hosts = mock.MagicMock()
        nova_util.nova.hosts.get.return_value = host
        result = nova_util.set_host_offline("rennes")
        self.assertEqual(True, result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_live_migrate_instance(self, mock_glance, mock_cinder,
                                   mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = mock.MagicMock()
        server.id = self.instance_uuid
        nova_util.nova.servers = mock.MagicMock()
        nova_util.nova.servers.list.return_value = [server]
        instance = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_hypervisor
        )
        self.assertIsNotNone(instance)

    def test_watcher_non_live_migrate_instance_not_found(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_util.nova.servers.list.return_value = []
        nova_util.nova.servers.find.return_value = None

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor)

        self.assertEqual(False, is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_watcher_non_live_migrate_instance_volume(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = mock.MagicMock(id=self.instance_uuid)
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        nova_util.nova.servers.list.return_value = [instance]
        nova_util.nova.servers.find.return_value = instance
        instance = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor)
        self.assertIsNotNone(instance)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_watcher_non_live_migrate_keep_image(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = mock.MagicMock(id=self.instance_uuid)
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        addresses = mock.MagicMock()
        network_type = mock.MagicMock()
        networks = []
        networks.append(("lan", network_type))
        addresses.items.return_value = networks
        attached_volumes = mock.MagicMock()
        setattr(instance, 'addresses', addresses)
        setattr(instance, "os-extended-volumes:volumes_attached",
                attached_volumes)
        nova_util.nova.servers.list.return_value = [instance]
        nova_util.nova.servers.find.return_value = instance
        instance = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor, keep_original_image_name=False)
        self.assertIsNotNone(instance)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_create_image_from_instance(self, mock_glance, mock_cinder,
                                        mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = mock.MagicMock()
        image = mock.MagicMock()
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        nova_util.nova.servers.list.return_value = [instance]
        nova_util.nova.servers.find.return_value = instance
        image_uuid = 'fake-image-uuid'
        nova_util.nova.servers.create_image.return_value = image

        glance_client = mock.MagicMock()
        mock_glance.return_value = glance_client

        glance_client.images = {image_uuid: image}
        instance = nova_util.create_image_from_instance(
            self.instance_uuid, "Cirros"
        )
        self.assertIsNone(instance)
