# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
import uuid
from watcher.common import exception

from watcher.decision_engine.framework.model.hypervisor import Hypervisor
from watcher.decision_engine.framework.model.model_root import ModelRoot

from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector

from watcher.tests import base


class TestModel(base.BaseTestCase):
    def test_model(self):
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_1()

        self.assertEqual(len(model._hypervisors), 5)
        self.assertEqual(len(model._vms), 35)
        self.assertEqual(len(model.get_mapping().get_mapping()), 5)

    def test_add_hypervisor(self):
        model = ModelRoot()
        id = str(uuid.uuid4())
        hypervisor = Hypervisor()
        hypervisor.set_uuid(id)
        model.add_hypervisor(hypervisor)
        self.assertEqual(model.get_hypervisor_from_id(id), hypervisor)

    def test_delete_hypervisor(self):
        model = ModelRoot()
        id = str(uuid.uuid4())
        hypervisor = Hypervisor()
        hypervisor.set_uuid(id)
        model.add_hypervisor(hypervisor)
        self.assertEqual(model.get_hypervisor_from_id(id), hypervisor)
        model.remove_hypervisor(hypervisor)
        self.assertRaises(exception.HypervisorNotFound,
                          model.get_hypervisor_from_id, id)
