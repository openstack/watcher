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

import mock

from watcher.common import nova_helper
from watcher.decision_engine.model.collector import nova
from watcher.tests import base
from watcher.tests import conf_fixture


class TestNovaClusterDataModelCollector(base.TestCase):

    def setUp(self):
        super(TestNovaClusterDataModelCollector, self).setUp()
        self.useFixture(conf_fixture.ConfReloadFixture())

    @mock.patch('keystoneclient.v3.client.Client', mock.Mock())
    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_nova_cdmc_execute(self, m_nova_helper_cls):
        m_nova_helper = mock.Mock(name="nova_helper")
        m_nova_helper_cls.return_value = m_nova_helper
        m_nova_helper.get_service.return_value = mock.Mock(
            id=1355,
            host='test_hostname',
            binary='nova-compute',
            status='enabled',
            state='up',
            disabled_reason='',
        )

        fake_compute_node = mock.Mock(
            id=1337,
            service={'id': 123},
            hypervisor_hostname='test_hostname',
            memory_mb=333,
            free_disk_gb=222,
            local_gb=111,
            vcpus=4,
            state='TEST_STATE',
            status='TEST_STATUS',
        )
        fake_instance = mock.Mock(
            id='ef500f7e-dac8-470f-960c-169486fce71b',
            human_id='fake_instance',
            flavor={'ram': 333, 'disk': 222, 'vcpus': 4, 'id': 1},
            metadata={'hi': 'hello'},
        )
        setattr(fake_instance, 'OS-EXT-STS:vm_state', 'VM_STATE')
        setattr(fake_instance, 'OS-EXT-SRV-ATTR:host', 'test_hostname')
        m_nova_helper.get_compute_node_list.return_value = [fake_compute_node]
        # m_nova_helper.get_instances_by_node.return_value = [fake_instance]
        m_nova_helper.get_instance_list.return_value = [fake_instance]

        m_config = mock.Mock()
        m_osc = mock.Mock()

        nova_cdmc = nova.NovaClusterDataModelCollector(
            config=m_config, osc=m_osc)

        model = nova_cdmc.execute()

        compute_nodes = model.get_all_compute_nodes()
        instances = model.get_all_instances()

        self.assertEqual(1, len(compute_nodes))
        self.assertEqual(1, len(instances))

        node = list(compute_nodes.values())[0]
        instance = list(instances.values())[0]

        self.assertEqual(node.uuid, 'test_hostname')
        self.assertEqual(instance.uuid, 'ef500f7e-dac8-470f-960c-169486fce71b')
