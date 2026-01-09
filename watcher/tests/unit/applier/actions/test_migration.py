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

from unittest import mock

import jsonschema


from watcher.applier.actions import base as baction
from watcher.applier.actions import migration
from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils


class TestMigration(test_utils.NovaResourcesMixin, base.TestCase):

    INSTANCE_UUID = "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba"

    def setUp(self):
        super().setUp()

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
            "source_node": "compute1-hostname",
            "destination_node": "compute2-hostname",
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
        }
        self.action = migration.Migrate(mock.Mock())
        self.action.input_parameters = self.input_parameters

        self.input_parameters_cold = {
            "migration_type": "cold",
            "source_node": "compute1-hostname",
            "destination_node": "compute2-hostname",
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
        }
        self.action_cold = migration.Migrate(mock.Mock())
        self.action_cold.input_parameters = self.input_parameters_cold

    def test_parameters(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.INSTANCE_UUID,
                  self.action.MIGRATION_TYPE: 'live',
                  self.action.DESTINATION_NODE: 'compute-2',
                  self.action.SOURCE_NODE: 'compute-3'}
        self.action.input_parameters = params
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_cold(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.INSTANCE_UUID,
                  self.action.MIGRATION_TYPE: 'cold',
                  self.action.DESTINATION_NODE: 'compute-2',
                  self.action.SOURCE_NODE: 'compute-3'}
        self.action_cold.input_parameters = params
        self.assertTrue(self.action_cold.validate_parameters())

    def test_parameters_exception_empty_fields(self):
        parameters = {baction.BaseAction.RESOURCE_ID: None,
                      'migration_type': None,
                      'source_node': None,
                      'destination_node': None}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_exception_migration_type(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      'migration_type': 'unknown',
                      'source_node': 'compute-2',
                      'destination_node': 'compute-3'}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_exception_source_node(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      'migration_type': 'live',
                      'source_node': None,
                      'destination_node': 'compute-3'}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_destination_node_none(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      'migration_type': 'live',
                      'source_node': 'compute-1',
                      'destination_node': None}
        self.action.input_parameters = parameters
        self.assertTrue(self.action.validate_parameters)

    def test_parameters_exception_resource_id(self):
        parameters = {baction.BaseAction.RESOURCE_ID: "EFEF",
                      'migration_type': 'live',
                      'source_node': 'compute-2',
                      'destination_node': 'compute-3'}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_migration_pre_condition_success(self):
        """Test successful pre_condition with all checks passing"""
        parameters = {baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
                      'migration_type': 'live',
                      'source_node': 'compute1-hostname',
                      'destination_node': 'compute2-hostname'}
        self.action.input_parameters = parameters
        instance_info = {
            'id': self.INSTANCE_UUID,
            'status': 'ACTIVE',
            'OS-EXT-SRV-ATTR:host': 'compute1-hostname'
        }
        instance = nova_helper.Server.from_novaclient(
            self.create_nova_server(**instance_info)
        )

        compute_node_info = {
            'id': 'f81d4fae-7dec-11d0-a765-00a0c91e6bf6',
            'status': 'enabled',
            'hypervisor_hostname': 'compute1-hostname',
            'service': {
                'host': 'compute1-hostname'
            }
        }
        compute_node = nova_helper.Hypervisor.from_novaclient(
            self.create_nova_hypervisor(**compute_node_info)
        )

        self.m_helper.find_instance.return_value = instance
        self.m_helper.get_compute_node_by_hostname.return_value = compute_node

        self.action.pre_condition()

    def test_pre_condition_instance_not_found(self):
        """Test pre_condition fails when instance doesn't exist"""
        err = exception.ComputeResourceNotFound()
        self.m_helper.find_instance.side_effect = err

        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Instance {self.INSTANCE_UUID} not found",
            self.action.pre_condition)

    def test_pre_condition_instance_on_wrong_host(self):
        """Test pre_condition fails when instance is on wrong host"""
        instance_info = {
            'id': self.INSTANCE_UUID,
            'status': 'ACTIVE',
            'OS-EXT-SRV-ATTR:host': 'wrong-hostname'
        }
        instance = nova_helper.Server.from_novaclient(
            self.create_nova_server(**instance_info)
        )

        self.m_helper.find_instance.return_value = instance

        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Instance {self.INSTANCE_UUID} is not running on source node "
            r"compute1-hostname \(currently on wrong-hostname\)",
            self.action.pre_condition)

    def test_pre_condition_destination_node_not_found(self):
        """Test pre_condition fails when destination node doesn't exist"""
        instance_info = {
            'id': self.INSTANCE_UUID,
            'status': 'ACTIVE',
            'OS-EXT-SRV-ATTR:host': 'compute1-hostname'
        }
        instance = nova_helper.Server.from_novaclient(
            self.create_nova_server(**instance_info)
        )

        self.m_helper.find_instance.return_value = instance
        self.m_helper.get_compute_node_by_hostname.side_effect = (
            exception.ComputeNodeNotFound(name='compute2-hostname'))

        self.assertRaisesRegex(
            exception.ActionExecutionFailure,
            "Destination node compute2-hostname not found",
            self.action.pre_condition)

    def test_pre_condition_destination_node_disabled(self):
        """Test pre_condition fails when destination node is disabled"""
        instance_info = {
            'id': self.INSTANCE_UUID,
            'status': 'ACTIVE',
            'OS-EXT-SRV-ATTR:host': 'compute1-hostname'
        }
        instance = nova_helper.Server.from_novaclient(
            self.create_nova_server(**instance_info)
        )

        compute_node_info = {
            'id': 'f81d4fae-7dec-11d0-a765-00a0c91e6bf6',
            'status': 'disabled',
            'hypervisor_hostname': 'compute2-hostname',
            'service': {
                'host': 'compute2-hostname'
            }
        }
        compute_node = nova_helper.Hypervisor.from_novaclient(
            self.create_nova_hypervisor(**compute_node_info)
        )

        self.m_helper.find_instance.return_value = instance
        self.m_helper.get_compute_node_by_hostname.return_value = compute_node

        self.assertRaisesRegex(
            exception.ActionExecutionFailure,
            "Destination node compute2-hostname is not in enabled state",
            self.action.pre_condition)

    def test_pre_condition_live_migration_wrong_status(self):
        """Test pre_condition fails live migration with non-ACTIVE status"""
        instance_info = {
            'id': self.INSTANCE_UUID,
            'status': 'SHUTOFF',
            'OS-EXT-SRV-ATTR:host': 'compute1-hostname'
        }
        instance = nova_helper.Server.from_novaclient(
            self.create_nova_server(**instance_info)
        )

        compute_node_info = {
            'id': 'f81d4fae-7dec-11d0-a765-00a0c91e6bf6',
            'status': 'enabled',
            'hypervisor_hostname': 'compute2-hostname',
            'service': {
                'host': 'compute2-hostname'
            }
        }
        compute_node = nova_helper.Hypervisor.from_novaclient(
            self.create_nova_hypervisor(**compute_node_info)
        )

        self.m_helper.find_instance.return_value = instance
        self.m_helper.get_compute_node_by_hostname.return_value = compute_node

        self.assertRaisesRegex(
            exception.ActionExecutionFailure,
            f"Live migration requires instance {self.INSTANCE_UUID} to be in "
            r"ACTIVE status \(current status: SHUTOFF\)",
            self.action.pre_condition)

    def test_pre_condition_no_destination_node(self):
        """Test pre_condition with no destination node specified"""
        instance_info = {
            'id': self.INSTANCE_UUID,
            'status': 'ACTIVE',
            'OS-EXT-SRV-ATTR:host': 'compute1-hostname'
        }
        instance = nova_helper.Server.from_novaclient(
            self.create_nova_server(**instance_info)
        )

        self.m_helper.find_instance.return_value = instance

        # Create action without destination_node
        params = {
            "migration_type": "live",
            "source_node": "compute1-hostname",
            "destination_node": None,
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
        }
        action = migration.Migrate(mock.Mock())
        action.input_parameters = params

        action.pre_condition()

        # Ensure get_compute_node_by_hostname was not called
        self.m_helper.get_compute_node_by_hostname.assert_not_called()

    def test_migration_post_condition(self):
        try:
            self.action.post_condition()
        except Exception as exc:
            self.fail(exc)

    def test_execute_live_migration_invalid_instance(self):
        self.m_helper.find_instance.side_effect = exception.InstanceNotFound(
            name=self.INSTANCE_UUID
        )
        exc = self.assertRaises(
            exception.InstanceNotFound, self.action.execute)
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)
        self.assertEqual(self.INSTANCE_UUID, exc.kwargs["name"])

    def test_execute_cold_migration_invalid_instance(self):
        self.m_helper.find_instance.side_effect = exception.InstanceNotFound(
            name=self.INSTANCE_UUID
        )
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
            dest_hostname="compute2-hostname")

    def test_execute_cold_migration(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        try:
            self.action_cold.execute()
        except Exception as exc:
            self.fail(exc)

        self.m_helper.watcher_non_live_migrate_instance.\
            assert_called_once_with(
                instance_id=self.INSTANCE_UUID,
                dest_hostname="compute2-hostname"
            )

    def test_revert_live_migration(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        self.action.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.live_migrate_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID,
            dest_hostname="compute1-hostname"
        )

    def test_revert_cold_migration(self):
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID

        self.action_cold.revert()

        self.m_helper_cls.assert_called_once_with(osc=self.m_osc)
        self.m_helper.watcher_non_live_migrate_instance.\
            assert_called_once_with(
                instance_id=self.INSTANCE_UUID,
                dest_hostname="compute1-hostname"
            )

    def test_abort_live_migrate(self):
        migration = mock.MagicMock()
        migration.id = "2"
        migrations = [migration]
        self.m_helper.get_running_migration.return_value = migrations
        self.m_helper.find_instance.return_value = self.INSTANCE_UUID
        try:
            self.action.abort()
        except Exception as exc:
            self.fail(exc)

        self.m_helper.abort_live_migrate.assert_called_once_with(
            instance_id=self.INSTANCE_UUID, source="compute1-hostname",
            destination="compute2-hostname")
