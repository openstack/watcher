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

import glanceclient.v2.client as glclient
import mock
import novaclient.client as nvclient

from watcher.common import keystone
from watcher.common.nova import NovaClient
from watcher.common import utils
from watcher.tests import base


class TestNovaClient(base.TestCase):

    def setUp(self):
        super(TestNovaClient, self).setUp()
        self.instance_uuid = "fb5311b7-37f3-457e-9cde-6494a3c59bfe"
        self.source_hypervisor = "ldev-indeedsrv005"
        self.destination_hypervisor = "ldev-indeedsrv006"

        self.creds = mock.MagicMock()
        self.session = mock.MagicMock()

    @mock.patch.object(keystone, 'KeystoneClient', mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_stop_instance(self):
        nova_client = NovaClient(creds=self.creds, session=self.session)
        instance_id = utils.generate_uuid()
        server = mock.MagicMock()
        server.id = instance_id
        setattr(server, 'OS-EXT-STS:vm_state', 'stopped')
        nova_client.nova.servers = mock.MagicMock()
        nova_client.nova.servers.find.return_value = server
        nova_client.nova.servers.list.return_value = [server]

        result = nova_client.stop_instance(instance_id)
        self.assertEqual(result, True)

    @mock.patch.object(keystone, 'KeystoneClient', mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_set_host_offline(self):
        nova_client = NovaClient(creds=self.creds, session=self.session)
        host = mock.MagicMock()
        nova_client.nova.hosts = mock.MagicMock()
        nova_client.nova.hosts.get.return_value = host
        result = nova_client.set_host_offline("rennes")
        self.assertEqual(result, True)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(keystone, 'KeystoneClient', mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_live_migrate_instance(self):
        nova_client = NovaClient(creds=self.creds, session=self.session)
        server = mock.MagicMock()
        server.id = self.instance_uuid
        nova_client.nova.servers = mock.MagicMock()
        nova_client.nova.servers.list.return_value = [server]
        instance = nova_client.live_migrate_instance(
            self.instance_uuid, self.destination_hypervisor
        )
        self.assertIsNotNone(instance)

    @mock.patch.object(keystone, 'KeystoneClient', mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_watcher_non_live_migrate_instance_not_found(self):
        nova_client = NovaClient(creds=self.creds, session=self.session)
        nova_client.nova.servers.list.return_value = []
        nova_client.nova.servers.find.return_value = None

        is_success = nova_client.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor)

        self.assertEqual(is_success, False)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(keystone, 'KeystoneClient', mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_watcher_non_live_migrate_instance_volume(self):
        nova_client = NovaClient(creds=self.creds, session=self.session)
        instance = mock.MagicMock(id=self.instance_uuid)
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        nova_client.nova.servers.list.return_value = [instance]
        nova_client.nova.servers.find.return_value = instance
        instance = nova_client.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor)
        self.assertIsNotNone(instance)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(keystone, 'KeystoneClient', mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_watcher_non_live_migrate_keep_image(self):
        nova_client = NovaClient(creds=self.creds, session=self.session)
        instance = mock.MagicMock(id=self.instance_uuid)
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        addresses = mock.MagicMock()
        type = mock.MagicMock()
        networks = []
        networks.append(("lan", type))
        addresses.items.return_value = networks
        attached_volumes = mock.MagicMock()
        setattr(instance, 'addresses', addresses)
        setattr(instance, "os-extended-volumes:volumes_attached",
                attached_volumes)
        nova_client.nova.servers.list.return_value = [instance]
        nova_client.nova.servers.find.return_value = instance
        instance = nova_client.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor, keep_original_image_name=False)
        self.assertIsNotNone(instance)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(keystone, 'KeystoneClient', mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    @mock.patch.object(glclient, "Client")
    def test_create_image_from_instance(self, m_glance_cls):
        nova_client = NovaClient(creds=self.creds, session=self.session)
        instance = mock.MagicMock()
        image = mock.MagicMock()
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        nova_client.nova.servers.list.return_value = [instance]
        nova_client.nova.servers.find.return_value = instance
        image_uuid = 'fake-image-uuid'
        nova_client.nova.servers.create_image.return_value = image

        m_glance = mock.MagicMock()
        m_glance_cls.return_value = m_glance

        m_glance.images = {image_uuid: image}
        instance = nova_client.create_image_from_instance(
            self.instance_uuid, "Cirros"
        )
        self.assertIsNone(instance)
