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
import mock
import time
from watcher.applier.framework.command.wrapper.nova_wrapper import NovaWrapper
from watcher.common import utils
from watcher.tests import base


class TestNovaWrapper(base.TestCase):
    @mock.patch('keystoneclient.v3.client.Client')
    def setUp(self, mock_ksclient):
        super(TestNovaWrapper, self).setUp()
        self.instance_uuid = "fb5311b7-37f3-457e-9cde-6494a3c59bfe"
        self.source_hypervisor = "ldev-indeedsrv005"
        self.destination_hypervisor = "ldev-indeedsrv006"

        self.creds = mock.MagicMock()
        self.session = mock.MagicMock()
        self.wrapper = NovaWrapper(creds=self.creds, session=self.session)

    def test_stop_instance(self):
        instance_id = utils.generate_uuid()
        server = mock.MagicMock()
        server.id = instance_id
        setattr(server, 'OS-EXT-STS:vm_state', 'stopped')
        self.wrapper.nova.servers = mock.MagicMock()
        self.wrapper.nova.servers.find.return_value = server
        self.wrapper.nova.servers.list.return_value = [server]

        result = self.wrapper.stop_instance(instance_id)
        self.assertEqual(result, True)

    def test_set_host_offline(self):
        host = mock.MagicMock()
        self.wrapper.nova.hosts = mock.MagicMock()
        self.wrapper.nova.hosts.get.return_value = host
        result = self.wrapper.set_host_offline("rennes")
        self.assertEqual(result, True)

    def test_live_migrate_instance(self):
        server = mock.MagicMock()
        server.id = self.instance_uuid
        self.wrapper.nova.servers = mock.MagicMock()
        self.wrapper.nova.servers.list.return_value = [server]
        with mock.patch.object(time, 'sleep'):
            instance = self.wrapper.live_migrate_instance(
                self.instance_uuid,
                self.destination_hypervisor)
            self.assertIsNotNone(instance)
