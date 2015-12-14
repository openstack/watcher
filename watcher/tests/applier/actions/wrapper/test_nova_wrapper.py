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
import keystoneclient.v3.client as ksclient
import mock
import novaclient.client as nvclient

from watcher.applier.primitives.wrapper.nova_wrapper import NovaWrapper
from watcher.common import utils
from watcher.tests import base


class TestNovaWrapper(base.TestCase):

    def setUp(self):
        super(TestNovaWrapper, self).setUp()
        self.instance_uuid = "fb5311b7-37f3-457e-9cde-6494a3c59bfe"
        self.source_hypervisor = "ldev-indeedsrv005"
        self.destination_hypervisor = "ldev-indeedsrv006"

        self.creds = mock.MagicMock()
        self.session = mock.MagicMock()

    @mock.patch.object(ksclient, "Client", mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_stop_instance(self):
        wrapper = NovaWrapper(creds=self.creds, session=self.session)
        instance_id = utils.generate_uuid()
        server = mock.MagicMock()
        server.id = instance_id
        setattr(server, 'OS-EXT-STS:vm_state', 'stopped')
        wrapper.nova.servers = mock.MagicMock()
        wrapper.nova.servers.find.return_value = server
        wrapper.nova.servers.list.return_value = [server]

        result = wrapper.stop_instance(instance_id)
        self.assertEqual(result, True)

    @mock.patch.object(ksclient, "Client", mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_set_host_offline(self):
        wrapper = NovaWrapper(creds=self.creds, session=self.session)
        host = mock.MagicMock()
        wrapper.nova.hosts = mock.MagicMock()
        wrapper.nova.hosts.get.return_value = host
        result = wrapper.set_host_offline("rennes")
        self.assertEqual(result, True)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(ksclient, "Client", mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_live_migrate_instance(self):
        wrapper = NovaWrapper(creds=self.creds, session=self.session)
        server = mock.MagicMock()
        server.id = self.instance_uuid
        wrapper.nova.servers = mock.MagicMock()
        wrapper.nova.servers.list.return_value = [server]
        instance = wrapper.live_migrate_instance(
            self.instance_uuid, self.destination_hypervisor
        )
        self.assertIsNotNone(instance)

    @mock.patch.object(ksclient, "Client", mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_watcher_non_live_migrate_instance_not_found(self):
        wrapper = NovaWrapper(creds=self.creds, session=self.session)
        wrapper.nova.servers.list.return_value = []
        wrapper.nova.servers.find.return_value = None

        is_success = wrapper.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor)

        self.assertEqual(is_success, False)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(ksclient, "Client", mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_watcher_non_live_migrate_instance_volume(self):
        wrapper = NovaWrapper(creds=self.creds, session=self.session)
        instance = mock.MagicMock(id=self.instance_uuid)
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        wrapper.nova.servers.list.return_value = [instance]
        wrapper.nova.servers.find.return_value = instance
        instance = wrapper.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor)
        self.assertIsNotNone(instance)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(ksclient, "Client", mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    def test_watcher_non_live_migrate_keep_image(self):
        wrapper = NovaWrapper(creds=self.creds, session=self.session)
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
        wrapper.nova.servers.list.return_value = [instance]
        wrapper.nova.servers.find.return_value = instance
        instance = wrapper.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_hypervisor, keep_original_image_name=False)
        self.assertIsNotNone(instance)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(ksclient, "Client", mock.Mock())
    @mock.patch.object(nvclient, "Client", mock.Mock())
    @mock.patch.object(glclient, "Client")
    def test_create_image_from_instance(self, m_glance_cls):
        wrapper = NovaWrapper(creds=self.creds, session=self.session)
        instance = mock.MagicMock()
        image = mock.MagicMock()
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_hypervisor)
        wrapper.nova.servers.list.return_value = [instance]
        wrapper.nova.servers.find.return_value = instance
        image_uuid = 'fake-image-uuid'
        wrapper.nova.servers.create_image.return_value = image

        m_glance = mock.MagicMock()
        m_glance_cls.return_value = m_glance

        m_glance.images = {image_uuid: image}
        instance = wrapper.create_image_from_instance(
            self.instance_uuid, "Cirros"
        )
        self.assertIsNone(instance)
