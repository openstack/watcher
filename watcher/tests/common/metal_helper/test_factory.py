# Copyright 2023 Cloudbase Solutions
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

from watcher.common import clients
from watcher.common.metal_helper import factory
from watcher.common.metal_helper import ironic
from watcher.common.metal_helper import maas
from watcher.tests import base


class TestMetalHelperFactory(base.TestCase):

    @mock.patch.object(clients, 'OpenStackClients')
    @mock.patch.object(maas, 'MaasHelper')
    @mock.patch.object(ironic, 'IronicHelper')
    def test_factory(self, mock_ironic, mock_maas, mock_osc):
        self.assertEqual(
            mock_ironic.return_value,
            factory.get_helper())

        self.config(url="fake_maas_url", group="maas_client")
        self.assertEqual(
            mock_maas.return_value,
            factory.get_helper())
