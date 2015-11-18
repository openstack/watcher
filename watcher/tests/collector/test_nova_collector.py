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

from watcher.metrics_engine.cluster_model_collector.nova import \
    NovaClusterModelCollector
from watcher.tests import base


class TestNovaCollector(base.TestCase):
    @mock.patch('keystoneclient.v3.client.Client')
    def setUp(self, mock_ksclient):
        super(TestNovaCollector, self).setUp()
        self.wrapper = mock.MagicMock()
        self.nova_collector = NovaClusterModelCollector(self.wrapper)

    def test_nova_collector(self):
        hypervisor = mock.Mock()
        hypervisor.hypervisor_hostname = "rdev-lannion.eu"
        hypervisor.service = mock.MagicMock()
        service = mock.Mock()
        service.host = ""
        self.wrapper.get_hypervisors_list.return_value = {hypervisor}
        self.wrapper.nova.services.find.get.return_value = service
        model = self.nova_collector.get_latest_cluster_data_model()
        self.assertIsNotNone(model)
