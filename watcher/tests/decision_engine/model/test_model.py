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

from watcher.common import exception
from watcher.decision_engine.model import hypervisor as hypervisor_model
from watcher.decision_engine.model import hypervisor_state
from watcher.decision_engine.model import model_root
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state


class TestModel(base.BaseTestCase):
    def test_model(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_1()

        self.assertEqual(5, len(model._hypervisors))
        self.assertEqual(35, len(model._vms))
        self.assertEqual(5, len(model.get_mapping().get_mapping()))

    def test_add_hypervisor(self):
        model = model_root.ModelRoot()
        id = "{0}".format(uuid.uuid4())
        hypervisor = hypervisor_model.Hypervisor()
        hypervisor.uuid = id
        model.add_hypervisor(hypervisor)
        self.assertEqual(hypervisor, model.get_hypervisor_from_id(id))

    def test_delete_hypervisor(self):
        model = model_root.ModelRoot()
        id = "{0}".format(uuid.uuid4())
        hypervisor = hypervisor_model.Hypervisor()
        hypervisor.uuid = id
        model.add_hypervisor(hypervisor)
        self.assertEqual(hypervisor, model.get_hypervisor_from_id(id))
        model.remove_hypervisor(hypervisor)
        self.assertRaises(exception.HypervisorNotFound,
                          model.get_hypervisor_from_id, id)

    def test_get_all_hypervisors(self):
        model = model_root.ModelRoot()
        for i in range(10):
            id = "{0}".format(uuid.uuid4())
            hypervisor = hypervisor_model.Hypervisor()
            hypervisor.uuid = id
            model.add_hypervisor(hypervisor)
        all_hypervisors = model.get_all_hypervisors()
        for id in all_hypervisors:
            hyp = model.get_hypervisor_from_id(id)
            model.assert_hypervisor(hyp)

    def test_set_get_state_hypervisors(self):
        model = model_root.ModelRoot()
        id = "{0}".format(uuid.uuid4())
        hypervisor = hypervisor_model.Hypervisor()
        hypervisor.uuid = id
        model.add_hypervisor(hypervisor)

        self.assertIsInstance(hypervisor.state,
                              hypervisor_state.HypervisorState)

        hyp = model.get_hypervisor_from_id(id)
        hyp.state = hypervisor_state.HypervisorState.OFFLINE
        self.assertIsInstance(hyp.state, hypervisor_state.HypervisorState)

    # /watcher/decision_engine/framework/model/hypervisor.py
    # set_state accept any char chain.
    # verification (IsInstance) should be used in the function
    #        hyp.set_state('blablabla')
    #       self.assertEqual(hyp.get_state(), 'blablabla')
    #        self.assertIsInstance(hyp.get_state(), HypervisorState)

    #    def test_get_all_vms(self):
    #        model = ModelRoot()
    #        vms = model.get_all_vms()
    #        self.assert(len(model._vms))
    def test_hypervisor_from_id_raise(self):
        model = model_root.ModelRoot()
        id = "{0}".format(uuid.uuid4())
        hypervisor = hypervisor_model.Hypervisor()
        hypervisor.uuid = id
        model.add_hypervisor(hypervisor)

        id2 = "{0}".format(uuid.uuid4())
        self.assertRaises(exception.HypervisorNotFound,
                          model.get_hypervisor_from_id, id2)

    def test_remove_hypervisor_raise(self):
        model = model_root.ModelRoot()
        id = "{0}".format(uuid.uuid4())
        hypervisor = hypervisor_model.Hypervisor()
        hypervisor.uuid = id
        model.add_hypervisor(hypervisor)

        id2 = "{0}".format(uuid.uuid4())
        hypervisor2 = hypervisor_model.Hypervisor()
        hypervisor2.uuid = id2

        self.assertRaises(exception.HypervisorNotFound,
                          model.remove_hypervisor, hypervisor2)

    def test_assert_hypervisor_raise(self):
        model = model_root.ModelRoot()
        id = "{0}".format(uuid.uuid4())
        hypervisor = hypervisor_model.Hypervisor()
        hypervisor.uuid = id
        model.add_hypervisor(hypervisor)
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_hypervisor, "objet_qcq")

    def test_vm_from_id_raise(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_1()
        self.assertRaises(exception.InstanceNotFound,
                          model.get_vm_from_id, "valeur_qcq")

    def test_assert_vm_raise(self):
        model = model_root.ModelRoot()
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_vm, "valeur_qcq")
