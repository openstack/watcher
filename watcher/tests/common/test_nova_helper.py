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
    def fake_nova_find_list(nova_util, find=None, list=None):
        nova_util.nova.servers.get.return_value = find
        if list is None:
            nova_util.nova.servers.list.return_value = []
        else:
            nova_util.nova.servers.list.return_value = [list]

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
        nova_services.disable.return_value = mock.MagicMock(
            status='enabled')

        result = nova_util.disable_service_nova_compute('nanjing')
        self.assertFalse(result)

        nova_services.disable.return_value = mock.MagicMock(
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
