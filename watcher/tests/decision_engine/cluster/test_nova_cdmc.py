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
        m_nova_helper = mock.Mock()
        m_nova_helper_cls.return_value = m_nova_helper
        fake_hypervisor = mock.Mock(
            service={'id': 123},
            hypervisor_hostname='test_hostname',
            memory_mb=333,
            free_disk_gb=222,
            local_gb=111,
            vcpus=4,
            state='TEST_STATE',
            status='TEST_STATUS',
        )
        fake_vm = mock.Mock(
            id='ef500f7e-dac8-470f-960c-169486fce71b',
            state=mock.Mock(**{'OS-EXT-STS:vm_state': 'VM_STATE'}),
            flavor={'ram': 333, 'disk': 222, 'vcpus': 4},
        )
        m_nova_helper.get_hypervisors_list.return_value = [fake_hypervisor]
        m_nova_helper.get_vms_by_hypervisor.return_value = [fake_vm]
        m_nova_helper.nova.services.find.return_value = mock.Mock(
            host='test_hostname')

        def m_get_flavor_instance(vm, cache):
            vm.flavor = {'ram': 333, 'disk': 222, 'vcpus': 4}
            return vm

        m_nova_helper.get_flavor_instance.side_effect = m_get_flavor_instance

        m_config = mock.Mock()
        m_osc = mock.Mock()

        nova_cdmc = nova.NovaClusterDataModelCollector(
            config=m_config, osc=m_osc)

        model = nova_cdmc.execute()

        hypervisors = model.get_all_hypervisors()
        vms = model.get_all_vms()

        self.assertEqual(1, len(hypervisors))
        self.assertEqual(1, len(vms))

        hypervisor = list(hypervisors.values())[0]
        vm = list(vms.values())[0]

        self.assertEqual(hypervisor.uuid, 'test_hostname')
        self.assertEqual(vm.uuid, 'ef500f7e-dac8-470f-960c-169486fce71b')
