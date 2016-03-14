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

from watcher.decision_engine.model import hypervisor as modelhyp
from watcher.decision_engine.model import vm_state
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies import \
    faker_cluster_state


class TestMapping(base.BaseTestCase):

    VM1_UUID = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
    VM2_UUID = "a4cab39b-9828-413a-bf88-f76921bf1517"

    def test_get_node_from_vm(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()

        vms = model.get_all_vms()
        keys = list(vms.keys())
        vm = vms[keys[0]]
        if vm.uuid != self.VM1_UUID:
            vm = vms[keys[1]]
        node = model.mapping.get_node_from_vm(vm)
        self.assertEqual('Node_0', node.uuid)

    def test_get_node_from_vm_id(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()

        hyps = model.mapping.get_node_vms_from_id("BLABLABLA")
        self.assertEqual(0, hyps.__len__())

    def test_get_all_vms(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()

        vms = model.get_all_vms()
        self.assertEqual(2, vms.__len__())
        self.assertEqual(vm_state.VMState.ACTIVE.value,
                         vms[self.VM1_UUID].state)
        self.assertEqual(self.VM1_UUID, vms[self.VM1_UUID].uuid)
        self.assertEqual(vm_state.VMState.ACTIVE.value,
                         vms[self.VM2_UUID].state)
        self.assertEqual(self.VM2_UUID, vms[self.VM2_UUID].uuid)

    def test_get_mapping(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()
        mapping_vm = model.mapping.get_mapping_vm()
        self.assertEqual(2, mapping_vm.__len__())
        self.assertEqual('Node_0', mapping_vm[self.VM1_UUID])
        self.assertEqual('Node_1', mapping_vm[self.VM2_UUID])

    def test_migrate_vm(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()
        vms = model.get_all_vms()
        keys = list(vms.keys())
        vm0 = vms[keys[0]]
        hyp0 = model.mapping.get_node_from_vm_id(vm0.uuid)
        vm1 = vms[keys[1]]
        hyp1 = model.mapping.get_node_from_vm_id(vm1.uuid)

        self.assertEqual(False, model.mapping.migrate_vm(vm1, hyp1, hyp1))
        self.assertEqual(False, model.mapping.migrate_vm(vm1, hyp0, hyp0))
        self.assertEqual(True, model.mapping.migrate_vm(vm1, hyp1, hyp0))
        self.assertEqual(True, model.mapping.migrate_vm(vm1, hyp0, hyp1))

    def test_unmap_from_id_log_warning(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()
        vms = model.get_all_vms()
        keys = list(vms.keys())
        vm0 = vms[keys[0]]
        id = "{0}".format(uuid.uuid4())
        hypervisor = modelhyp.Hypervisor()
        hypervisor.uuid = id

        model.mapping.unmap_from_id(hypervisor.uuid, vm0.uuid)
        # self.assertEqual(len(model.mapping.get_node_vms_from_id(
        # hypervisor.uuid)), 1)

    def test_unmap_from_id(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()
        vms = model.get_all_vms()
        keys = list(vms.keys())
        vm0 = vms[keys[0]]
        hyp0 = model.mapping.get_node_from_vm_id(vm0.uuid)

        model.mapping.unmap_from_id(hyp0.uuid, vm0.uuid)
        self.assertEqual(0, len(model.mapping.get_node_vms_from_id(
            hyp0.uuid)))
