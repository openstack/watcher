# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

from __future__ import unicode_literals

import mock
import voluptuous

from watcher.applier.actions import base as baction
from watcher.applier.actions import migration
from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.tests import base


class TestMigration(base.TestCase):

    INSTANCE_UUID = "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba"

    def setUp(self):
        super(TestMigration, self).setUp()

        self.m_osc_cls = mock.Mock()
        self.m_helper_cls = mock.Mock()
        self.m_helper = mock.Mock(spec=nova_helper.NovaHelper)
        self.m_helper_cls.return_value = self.m_helper
        self.m_osc = mock.Mock(spec=clients.OpenStackClients)
        self.m_osc_cls.return_value = self.m_osc

        m_openstack_clients = mock.patch.object(
            clients, "OpenStackClients", self.m_osc_cls)
        m_nova_helper = mock.patch.object(
            nova_helper, "NovaHelper", self.m_helper_cls)

        m_openstack_clients.start()
        m_nova_helper.start()

        self.addCleanup(m_openstack_clients.stop)
        self.addCleanup(m_nova_helper.stop)

        self.input_parameters = {
            "migration_type": "live",
            "src_hypervisor": "hypervisor1-hostname",
            "dst_hypervisor": "hypervisor2-hostname",
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
        }
        self.action = migration.Migrate(mock.Mock())
        self.action.input_parameters = self.input_parameters

        self.input_parameters_cold = {
            "migration_type": "cold",
            "src_hypervisor": "hypervisor1-hostname",
            "dst_hypervisor": "hypervisor2-hostname",
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
        }
        self.action_cold = migration.Migrate(mock.Mock())
        self.action_cold.input_parameters = self.input_parameters_cold

    def test_parameters(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.INSTANCE_UUID,
                  self.action.MIGRATION_TYPE: 'live',
                  self.action.DST_HYPERVISOR: 'compute-2',
                  self.action.SRC_HYPERVISOR: 'compute-3'}
        self.action.input_parameters = params
        self.assertEqual(True, self.action.validate_parameters())

    def test_parameters_cold(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.INSTANCE_UUID,
                  self.action.MIGRATION_TYPE: 'cold',
                  self.action.DST_HYPERVISOR: 'compute-2',
                  self.action.SRC_HYPERVISOR: 'compute-3'}
        self.action_cold.input_parameters = params
        self.assertEqual(True, self.action_cold.validate_parameters())

    def test_parameters_exception_empty_fields(self):
        parameters = {baction.BaseAction.RESOURCE_ID: None,
                      'migration_type': None,
                      'src_hypervisor': None,
                      'dst_hypervisor': None}
        self.action.input_parameters = parameters
        exc = self.assertRaises(
            voluptuous.MultipleInvalid, self.action.validate_parameters)
        self.assertEqual(
            sorted([(['migration_type'], voluptuous.ScalarInvalid),
                    (['src_hypervisor'], voluptuous.TypeInvalid),
                    (['dst_hypervisor'], voluptuous.TypeInvalid)]),
            sorted([(e.path, type(e)) for e in exc.errors]))

    def test_parameters_exception_migration_type(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      'migration_type': 'unknown',
                      'src_hypervisor': 'compute-2',
                      'dst_hypervisor': 'compute-3'}
        self.action.input_parameters = parameters
        exc = self.assertRaises(
            voluptuous.Invalid, self.action.validate_parameters)
        self.assertEqual(
            [(['migration_type'], voluptuous.ScalarInvalid)],
            [(e.path, type(e)) for e in exc.errors])

    def test_parameters_exception_src_hypervisor(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      'migration_type': 'live',
                      'src_hypervisor': None,
                      'dst_hypervisor': 'compute-3'}
        self.action.input_parameters = parameters
        exc = self.assertRaises(
            voluptuous.MultipleInvalid, self.action.validate_parameters)
        self.assertEqual(
            [(['src_hypervisor'], voluptuous.TypeInvalid)],
            [(e.path, type(e)) for e in exc.errors])

    def test_parameters_exception_dst_hypervisor(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      'migration_type': 'live',
                      'src_hypervisor': 'compute-1',
                      'dst_hypervisor': None}
        self.action.input_parameters = parameters
        exc = self.assertRaises(
            voluptuous.MultipleInvalid, self.action.validate_parameters)
        self.assertEqual(
            [(['dst_hypervisor'], voluptuous.TypeInvalid)],
            [(e.path, type(e)) for e in exc.errors])

    def test_parameters_exception_resource_id(self):
        parameters = {baction.BaseAction.RESOURCE_ID: "EFEF",
                      'migration_type': 'live',
                      'src_hypervisor': 'compute-2',
                      'dst_hypervisor': 'compute-3'}
        self.action.input_parameters = parameters
        exc = self.assertRaises(
            voluptuous.MultipleInvalid, self.action.validate_parameters)
        self.assertEqual(
            [(['resource_id'], voluptuous.Invalid)],
            [(e.path, type(e)) for e in exc.errors])

    def test_migration_precondition(self):
        try:
            self.action.precondition()
        except Exception as exc:
            self.fail(exc)

    def test_migration_postcondition(self):
        try:
            self.action.postcondition()
        except Exception as exc:
            self.fail(exc)

    def test_execute_live_migration_invalid_instance(self):
        self.m_helper.find_instance.return_value = None
        exc = self.assertRaises(
            exception.InstanceNotFound, self.action.execute)
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)
        self.assertEqual(self.INSTANCE_UUID, exc.kwargs["name"])

    def test_execute_cold_migration_invalid_instance(self):
        self.m_helper.find_instance.return_value = None
        exc = self.assertRaises(
            exception.InstanceNotFound, self.action_cold.execute)
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)
        self.assertEqual(self.INSTANCE_UUID, exc.kwargs["name"])

    def test_execute_live_migration(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        try:
            self.action.execute()
        except Exception as exc:
            self.fail(exc)

        self.m_helper.live_migrate_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID,
            dest_hostname="hypervisor2-hostname")

    def test_execute_cold_migration(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        try:
            self.action_cold.execute()
        except Exception as exc:
            self.fail(exc)

        self.m_helper.watcher_non_live_migrate_instance.\
            assert_called_once_with(
                instance_id=self.INSTANCE_UUID,
                dest_hostname="hypervisor2-hostname"
            )

    def test_revert_live_migration(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        self.action.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.live_migrate_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID,
            dest_hostname="hypervisor1-hostname"
        )

    def test_revert_cold_migration(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        self.action_cold.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.watcher_non_live_migrate_instance.\
            assert_called_once_with(
                instance_id=self.INSTANCE_UUID,
                dest_hostname="hypervisor1-hostname"
            )

    def test_live_migrate_non_shared_storage_instance(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        self.m_helper.live_migrate_instance.side_effect = [
            nova_helper.nvexceptions.ClientException(400, "BadRequest"), True]

        try:
            self.action.execute()
        except Exception as exc:
            self.fail(exc)

        self.m_helper.live_migrate_instance.assert_has_calls([
            mock.call(instance_id=self.INSTANCE_UUID,
                      dest_hostname="hypervisor2-hostname"),
            mock.call(instance_id=self.INSTANCE_UUID,
                      dest_hostname="hypervisor2-hostname",
                      block_migration=True)
            ])

        expected = [mock.call.first(instance_id=self.INSTANCE_UUID,
                                    dest_hostname="hypervisor2-hostname"),
                    mock.call.second(instance_id=self.INSTANCE_UUID,
                                     dest_hostname="hypervisor2-hostname",
                                     block_migration=True)
                    ]
        self.m_helper.live_migrate_instance.mock_calls == expected
        self.assertEqual(2, self.m_helper.live_migrate_instance.call_count)
