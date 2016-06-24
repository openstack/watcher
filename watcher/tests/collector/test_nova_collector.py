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

from watcher.common import nova_helper
from watcher.metrics_engine.cluster_model_collector import nova
from watcher.tests import base


class TestNovaCollector(base.TestCase):

    @mock.patch('keystoneclient.v3.client.Client', mock.Mock())
    @mock.patch.object(nova_helper, 'NovaHelper')
    def setUp(self, m_nova_helper):
        super(TestNovaCollector, self).setUp()
        self.m_nova_helper = m_nova_helper
        self.nova_collector = nova.NovaClusterDataModelCollector(
            config=mock.Mock())

    def test_nova_collector(self):
        hypervisor = mock.Mock()
        hypervisor.hypervisor_hostname = "compute-1"
        hypervisor.service = mock.MagicMock()
        service = mock.Mock()
        service.host = ""
        self.m_nova_helper.get_hypervisors_list.return_value = {hypervisor}
        self.m_nova_helper.nova.services.find.get.return_value = service
        model = self.nova_collector.get_latest_cluster_data_model()
        self.assertIsNotNone(model)
