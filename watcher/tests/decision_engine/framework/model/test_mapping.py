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
import uuid
from watcher.decision_engine.framework.model.hypervisor import Hypervisor
from watcher.decision_engine.framework.model.vm_state import VMState
from watcher.tests import base
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector


class TestMapping(base.BaseTestCase):
    def test_get_node_from_vm(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()

        vms = model.get_all_vms()
        keys = vms.keys()
        vm = vms[keys[0]]
        if vm.uuid != 'VM_0':
            vm = vms[keys[1]]
        node = model.mapping.get_node_from_vm(vm)
        self.assertEqual(node.uuid, 'Node_0')

    def test_get_node_from_vm_id(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()

        hyps = model.mapping.get_node_vms_from_id("BLABLABLA")
        self.assertEqual(hyps.__len__(), 0)

    def test_get_all_vms(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()

        vms = model.get_all_vms()
        self.assertEqual(vms.__len__(), 2)
        self.assertEqual(vms['VM_0'].state, VMState.ACTIVE.value)
        self.assertEqual(vms['VM_0'].uuid, 'VM_0')
        self.assertEqual(vms['VM_1'].state, VMState.ACTIVE.value)
        self.assertEqual(vms['VM_1'].uuid, 'VM_1')

    def test_get_mapping(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()

        mapping_vm = model.mapping.get_mapping_vm()
        self.assertEqual(mapping_vm.__len__(), 2)
        self.assertEqual(mapping_vm['VM_0'], 'Node_0')
        self.assertEqual(mapping_vm['VM_1'], 'Node_1')

    def test_migrate_vm(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()
        vms = model.get_all_vms()
        keys = vms.keys()
        vm0 = vms[keys[0]]
        hyp0 = model.mapping.get_node_from_vm_id(vm0.uuid)
        vm1 = vms[keys[1]]
        hyp1 = model.mapping.get_node_from_vm_id(vm1.uuid)

        self.assertEqual(model.mapping.migrate_vm(vm1, hyp1, hyp1), False)
        self.assertEqual(model.mapping.migrate_vm(vm1, hyp0, hyp0), False)
        self.assertEqual(model.mapping.migrate_vm(vm1, hyp1, hyp0), True)
        self.assertEqual(model.mapping.migrate_vm(vm1, hyp0, hyp1), True)

    def test_unmap_from_id_log_warning(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()
        vms = model.get_all_vms()
        keys = vms.keys()
        vm0 = vms[keys[0]]
        id = str(uuid.uuid4())
        hypervisor = Hypervisor()
        hypervisor.uuid = id

        model.mapping.unmap_from_id(hypervisor.uuid, vm0.uuid)
        # self.assertEqual(len(model.mapping.get_node_vms_from_id(
        # hypervisor.uuid)), 1)

    def test_unmap_from_id(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()
        vms = model.get_all_vms()
        keys = vms.keys()
        vm0 = vms[keys[0]]
        hyp0 = model.mapping.get_node_from_vm_id(vm0.uuid)

        model.mapping.unmap_from_id(hyp0.uuid, vm0.uuid)
        self.assertEqual(len(model.mapping.get_node_vms_from_id(
            hyp0.uuid)), 0)
