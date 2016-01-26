# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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
import voluptuous

from watcher.applier.actions import base as baction
from watcher.applier.actions import migration
from watcher.tests import base


class TestMigration(base.TestCase):
    def setUp(self):
        super(TestMigration, self).setUp()
        self.mig = migration.Migrate()

    def test_parameters(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba",
                  self.mig.MIGRATION_TYPE: 'live',
                  self.mig.DST_HYPERVISOR: 'compute-2',
                  self.mig.SRC_HYPERVISOR: 'compute3'}
        self.mig.input_parameters = params
        self.assertEqual(True, self.mig.validate_parameters())

    def test_parameters_exception_resource_id(self):
        parameters = {baction.BaseAction.RESOURCE_ID: "EFEF",
                      'migration_type': 'live',
                      'src_hypervisor': 'compute-2',
                      'dst_hypervisor': 'compute3'}
        self.mig.input_parameters = parameters
        self.assertRaises(voluptuous.Invalid, self.mig.validate_parameters)

    def test_parameters_exception_migration_type(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba",
                      'migration_type': 'cold',
                      'src_hypervisor': 'compute-2',
                      'dst_hypervisor': 'compute3'}
        self.mig.input_parameters = parameters
        self.assertRaises(voluptuous.Invalid, self.mig.validate_parameters)

    def test_parameters_exception_src_hypervisor(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba",
                      'migration_type': 'cold',
                      'src_hypervisor': None,
                      'dst_hypervisor': 'compute3'}
        self.mig.input_parameters = parameters
        self.assertRaises(voluptuous.Invalid, self.mig.validate_parameters)

    def test_parameters_exception_dst_hypervisor(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba",
                      'migration_type': 'cold',
                      'src_hypervisor': 'compute-1',
                      'dst_hypervisor': None}
        self.mig.input_parameters = parameters
        self.assertRaises(voluptuous.Invalid, self.mig.validate_parameters)

    def test_parameters_exception_empty_fields(self):
        parameters = {baction.BaseAction.RESOURCE_ID: None,
                      'migration_type': None,
                      'src_hypervisor': None,
                      'dst_hypervisor': None}
        self.mig.input_parameters = parameters
        self.assertRaises(voluptuous.Invalid, self.mig.validate_parameters)
