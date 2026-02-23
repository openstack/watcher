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

import fixtures
import time
from unittest import mock

from keystoneauth1 import exceptions as ksa_exc
from openstack import exceptions as sdk_exc


from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import utils
from watcher import conf
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils

CONF = conf.CONF


@mock.patch.object(clients.OpenStackClients, 'cinder')
class TestNovaHelper(test_utils.NovaResourcesMixin, base.TestCase):

    def setUp(self):
        super().setUp()
        self.instance_uuid = "fb5311b7-37f3-457e-9cde-6494a3c59bfe"
        self.source_node = "ldev-indeedsrv005"
        self.destination_node = "ldev-indeedsrv006"
        self.flavor_name = "x1"
        self.mock_sleep = self.useFixture(
            fixtures.MockPatchObject(time, 'sleep')).mock
        self.mock_connection = self.useFixture(
            fixtures.MockPatch("watcher.common.clients.get_sdk_connection")
        ).mock.return_value

    @staticmethod
    def fake_nova_find_list(mock_connection, fake_find=None, fake_list=None):
        mock_connection.compute.get_server.return_value = fake_find
        if fake_list is None:
            mock_connection.compute.servers.return_value = []
        # check if fake_list is a list and return it
        elif isinstance(fake_list, list):
            mock_connection.compute.servers.return_value = fake_list
        else:
            mock_connection.compute.servers.return_value = [fake_list]

    @staticmethod
    def fake_nova_hypervisor_list(mock_conn, fake_find=None, fake_list=None):
        mock_conn.compute.get_hypervisor.return_value = fake_find
        mock_conn.compute.hypervisors.return_value = fake_list

    @staticmethod
    def fake_nova_migration_list(mock_connection, fake_list=None):
        if fake_list is None:
            mock_connection.compute.server_migrations.return_value = []
        else:
            mock_connection.compute.server_migrations.return_value = [
                fake_list
            ]

    def test_get_compute_node_by_hostname(
            self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        hypervisor_id = utils.generate_uuid()
        hypervisor_name = "fake_hypervisor_1"
        hypervisor = self.create_openstacksdk_hypervisor(
            id=hypervisor_id,
            name=hypervisor_name
        )
        self.mock_connection.compute.hypervisors.return_value = [hypervisor]
        # verify that the compute node can be obtained normally by name
        compute_node = nova_util.get_compute_node_by_hostname(hypervisor_name)
        self.assertEqual(
            compute_node, nova_helper.Hypervisor.from_openstacksdk(hypervisor))

        # verify that getting the compute node with the wrong name
        # will throw an exception.
        self.assertRaises(
            exception.ComputeNodeNotFound,
            nova_util.get_compute_node_by_hostname,
            "exception_hypervisor_1")

        # verify that when the result of getting the compute node is empty
        # will throw an exception.
        self.mock_connection.compute.hypervisors.return_value = []
        self.assertRaises(
            exception.ComputeNodeNotFound,
            nova_util.get_compute_node_by_hostname,
            hypervisor_name)

    def test_get_compute_node_by_hostname_multiple_matches(self, mocks_cinder):
        # Tests a scenario where get_compute_node_by_name returns multiple
        # hypervisors and we have to pick the exact match based on the given
        # compute service hostname.
        nova_util = nova_helper.NovaHelper()
        nodes = []
        # compute1 is a substring of compute10 to trigger the fuzzy match.
        for hostname in ('compute1', 'compute10'):
            node = self.create_openstacksdk_hypervisor(
                id=utils.generate_uuid(),
                name=hostname,
                service_details={'host': hostname}
            )
            nodes.append(node)
        # We should get back exact matches based on the service host.
        self.mock_connection.compute.hypervisors.return_value = nodes
        for index, name in enumerate(['compute1', 'compute10']):
            result = nova_util.get_compute_node_by_hostname(name)
            self.assertEqual(
                nova_helper.Hypervisor.from_openstacksdk(nodes[index]), result)

    def test_get_compute_node_by_uuid(
            self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        hypervisor_id = utils.generate_uuid()
        hypervisor_name = "fake_hypervisor_1"
        hypervisor = self.create_openstacksdk_hypervisor(
            id=hypervisor_id,
            name=hypervisor_name
        )
        self.mock_connection.compute.get_hypervisor.return_value = hypervisor
        # verify that the compute node can be obtained normally by id
        compute_node = nova_util.get_compute_node_by_uuid(hypervisor_id)
        self.assertEqual(
            compute_node, nova_helper.Hypervisor.from_openstacksdk(hypervisor)
        )

    def test_get_instance_list(self, *args):
        nova_util = nova_helper.NovaHelper()
        # Call it once with no filters.
        result = nova_util.get_instance_list()
        self.mock_connection.compute.servers.assert_called_once_with(
            details=True, all_projects=True, marker=None
        )
        self.assertEqual([], result)
        self.mock_connection.compute.servers.reset_mock()
        # Call it again with filters.
        result = nova_util.get_instance_list(
            filters={'host': 'fake-host'}, limit=2
        )
        self.mock_connection.compute.servers.assert_called_once_with(
            details=True, all_projects=True, compute_host='fake-host',
            limit=2, marker=None
        )
        self.assertEqual([], result)

    def test_stop_instance(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        # verify that the method will return True when stopped
        kwargs = {
            "id": instance_id,
            "vm_state": "stopped"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection,
            fake_find=server,
            fake_list=server)

        result = nova_util.stop_instance(instance_id)
        self.assertTrue(result)

        # verify that the method will return False when active
        kwargs = {
            "id": instance_id,
            "vm_state": "active"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=None
        )

        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

        # verify that the method will return True when the state of instance
        # is in the expected state.
        with mock.patch.object(
            nova_util,
            'wait_for_instance_state',
            return_value=True
        ) as mock_instance_state:
            result = nova_util.stop_instance(instance_id)
            self.assertTrue(result)
            mock_instance_state.assert_called_once_with(
                mock.ANY,
                "stopped",
                8,
                10)

        # verify that the method stop_instance will return False when the
        # server is not available.
        err = sdk_exc.NotFoundException()
        self.mock_connection.compute.get_server.side_effect = err
        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

    def test_start_instance(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        # verify that the method will return True when active
        kwargs = {
            "id": instance_id,
            "vm_state": "active"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection,
            fake_find=server,
            fake_list=server)

        result = nova_util.start_instance(instance_id)
        self.assertTrue(result)

        # verify that the method will return False when stopped
        kwargs = {
            "id": instance_id,
            "vm_state": "stopped"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=None
        )

        result = nova_util.start_instance(instance_id)
        self.assertFalse(result)

        # verify that the method will return True when the state of instance
        # is in the expected state.
        with mock.patch.object(
            nova_util,
            'wait_for_instance_state',
            return_value=True
        ) as mock_instance_state:
            result = nova_util.start_instance(instance_id)
            self.assertTrue(result)
            mock_instance_state.assert_called_once_with(
                mock.ANY,
                "active",
                8,
                10)

        # verify that the method start_instance will return False when the
        # server is not available.
        err = sdk_exc.NotFoundException()
        self.mock_connection.compute.get_server.side_effect = err
        result = nova_util.start_instance(instance_id)
        self.assertFalse(result)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_resize', autospec=True
    )
    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_confirm_resize', autospec=True
    )
    def test_resize_instance(self, mock_confirm_resize, mock_resize,
                             mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "VERIFY_RESIZE",
            "vm_state": "resized"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection,
            fake_find=server,
            fake_list=server)
        flavor = self.create_openstacksdk_flavor(
            id=self.flavor_name, name=self.flavor_name
        )
        self.mock_connection.compute.get_flavor.return_value = flavor
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertTrue(is_success)
        mock_resize.assert_called_once_with(
            nova_util, self.instance_uuid, self.flavor_name
        )
        self.assertEqual(1, mock_confirm_resize.call_count)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_resize', autospec=True
    )
    def test_resize_instance_wrong_status(self, mock_resize, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "SOMETHING_ELSE",
            "vm_state": "resizing"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection,
            fake_find=server,
            fake_list=server)
        flavor = self.create_openstacksdk_flavor(
            id=self.flavor_name, name=self.flavor_name
        )
        self.mock_connection.compute.get_flavor.return_value = flavor
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertFalse(is_success)
        mock_resize.assert_called_once_with(
            nova_util, self.instance_uuid, self.flavor_name
        )

    def test_watcher_resize_instance_retry_success(self, mock_cinder):
        """Test that resize_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "RESIZING",
            "vm_state": "resizing"
        }
        server = self.create_openstacksdk_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "status": "VERIFY_RESIZE",
            "vm_state": "resized"
        }
        resized_server = self.create_openstacksdk_server(**kwargs)

        # This means instance will be found as VERIFY_RESIZE in second retry
        self.mock_connection.compute.get_server.side_effect = (server, server,
                                                               resized_server)

        self.mock_connection.compute.confirm_resize.return_value = True

        self.flags(migration_max_retries=20, migration_interval=4,
                   group='nova')
        # Resize will succeed because status changes to VERIFY_RESIZE
        is_success = nova_util.resize_instance(
            self.instance_uuid, self.flavor_name
        )

        # Should succeed
        self.assertTrue(is_success)
        # It will sleep 2 times because it will be found as VERIFY_RESIZE in
        # the second retry
        self.assertEqual(2, self.mock_sleep.call_count)
        # Verify all sleep calls used 4 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 4)

    def test_watcher_resize_instance_retry_default(self, mock_cinder):
        """Test that resize_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "RESIZING",
            "vm_state": "resizing"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(self.mock_connection, fake_find=server)

        # Resize will timeout because status never changes
        is_success = nova_util.resize_instance(
            self.instance_uuid, self.flavor_name
        )

        # Should fail due to timeout
        self.assertFalse(is_success)
        # With default migration_max_retries and migration_interval, should
        # sleep 180 times for 5 seconds
        self.assertEqual(180, self.mock_sleep.call_count)
        # Verify sleep calls used 5 second
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    def test_watcher_resize_instance_retry_custom(self, mock_cinder):
        """Test that watcher_non_live_migrate respects explicit retry value"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "RESIZING",
            "vm_state": "resizing"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(self.mock_connection, fake_find=server)

        # Set config to a custom values to ensure custom values are used
        self.flags(migration_max_retries=10,
                   migration_interval=3, group='nova')

        is_success = nova_util.resize_instance(
            self.instance_uuid, self.flavor_name
        )

        # Should fail due to timeout
        self.assertFalse(is_success)
        # It should sleep migration_max_retries times with migration_interval
        # seconds
        self.assertEqual(10, self.mock_sleep.call_count)
        # Verify all sleep calls used migration_interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 3)

    def test_live_migrate_instance(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.destination_node
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection,
            fake_find=server,
            fake_list=server)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "task_state": "migrating"
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=None
        )
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

        # verify that the method will return False when the instance does
        # not exist.
        err = sdk_exc.NotFoundException()
        self.mock_connection.compute.get_server.side_effect = err

        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

        # verify that the method will return False when the instance status
        # is in other cases.
        server.status = 'fake_status'
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=None
        )
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )
        self.assertFalse(is_success)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_with_task_state(
        self, mock_migrate, mock_cinder
    ):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "task_state": ""
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=None
        )
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.mock_sleep.assert_not_called()

        kwargs["task_state"] = 'migrating'
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.mock_sleep.assert_called_with(5)
        mock_migrate.assert_called_with(
            nova_util, self.instance_uuid, self.destination_node
        )

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_no_destination_node(
            self, mock_migrate, mock_cinder
    ):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_openstacksdk_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.destination_node,
            "status": "ACTIVE"
        }
        migrated_server = self.create_openstacksdk_server(**kwargs)

        self.mock_connection.compute.get_server.side_effect = (
            server, server, migrated_server
        )

        # Migration will success as will transition from migrating to ACTIVE
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, None
        )
        # Should succeed
        self.assertTrue(is_success)

    def test_watcher_non_live_migrate_instance_not_found(
            self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        err = sdk_exc.NotFoundException()
        self.mock_connection.compute.get_server.side_effect = err

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node)

        self.assertFalse(is_success)

    def test_abort_live_migrate_instance(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "task_state": None
        }
        server = self.create_openstacksdk_server(**kwargs)
        migration = self.create_openstacksdk_migration(id=2)
        self.fake_nova_migration_list(
            self.mock_connection, fake_list=migration
        )

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        self.assertTrue(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.destination_node,
            "task_state": None
        }
        server = self.create_openstacksdk_server(**kwargs)

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        self.assertFalse(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        server.status = 'ERROR'
        self.assertRaises(
            Exception,
            nova_util.abort_live_migrate,
            self.instance_uuid,
            self.source_node,
            self.destination_node)

        kwargs = {
            "id": self.instance_uuid,
            "task_state": "fake_task_state",
            "compute_host": self.destination_node
        }
        server = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=None
        )
        self.fake_nova_migration_list(self.mock_connection, fake_list=None)
        self.assertFalse(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_migrate', autospec=True
    )
    @mock.patch.object(nova_helper.NovaHelper, 'confirm_resize', autospec=True)
    def test_non_live_migrate_instance_no_destination_node(
            self, mock_confirm_resize, mock_migrate, mock_cinder
    ):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_openstacksdk_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.destination_node,
            "status": "VERIFY_RESIZE"
        }
        migrated_server = self.create_openstacksdk_server(**kwargs)

        self.mock_connection.compute.get_server.side_effect = (
            server, server, server, migrated_server)

        self.destination_node = None
        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, None
        )
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, None
        )
        self.assertEqual(1, mock_confirm_resize.call_count)
        self.assertTrue(is_success)

    @mock.patch.object(nova_helper.NovaHelper, 'confirm_resize', autospec=True)
    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_migrate', autospec=True
    )
    def test_watcher_non_live_migrate_instance_retry_success(
            self, mock_migrate, mock_confirm_resize, mock_cinder):
        """Test that watcher_non_live_migrate uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": 'MIGRATING',  # Never reaches ACTIVE
            "compute_host": self.source_node
        }
        server = self.create_openstacksdk_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "status": 'VERIFY_RESIZE',
            "compute_host": self.destination_node
        }
        verify_server = self.create_openstacksdk_server(**kwargs)

        # This means instance will be found as VERIFY_RESIZE in second retry
        self.mock_connection.compute.get_server.side_effect = (
            server, server, server, verify_server
        )

        mock_confirm_resize.return_value = True

        self.flags(migration_max_retries=20, migration_interval=4,
                   group='nova')
        # Migration will success as will transition from MIGRATING to
        # VERIFY_RESIZE
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, self.destination_node)
        # Should succeed
        self.assertTrue(is_success)
        # It will sleep 2 times because it will be found as VERIFY_RESIZE in
        # the second retry
        self.assertEqual(2, self.mock_sleep.call_count)
        # Verify all sleep calls used 4 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 4)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_migrate', autospec=True
    )
    def test_watcher_non_live_migrate_instance_retry_default(
            self, mock_migrate, mock_cinder):
        """Test that watcher_non_live_migrate uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_openstacksdk_server(**kwargs)

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        # Migration will timeout because status never changes
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, self.destination_node)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With default migration_max_retries and migration_interval, should
        # sleep 180 times for 5 seconds
        self.assertEqual(180, self.mock_sleep.call_count)
        # Verify sleep calls used 5 second
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_migrate', autospec=True
    )
    def test_watcher_non_live_migrate_instance_retry_custom(
            self, mock_migrate, mock_cinder):
        """Test that watcher_non_live_migrate respects explicit retry value"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "status": 'MIGRATING'  # Never reaches ACTIVE
        }
        server = self.create_openstacksdk_server(**kwargs)

        # Set config to a custom values to ensure custom values are used
        self.flags(migration_max_retries=10, migration_interval=3,
                   group='nova')

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, self.destination_node)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # It should sleep migration_max_retries times with migration_interval
        # seconds
        self.assertEqual(10, self.mock_sleep.call_count)
        # Verify all sleep calls used migration_interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 3)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_retry_default_success(
            self, mock_migrate, mock_cinder
    ):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "task_state": "migrating"
        }
        server = self.create_openstacksdk_server(**kwargs)

        kwargs["compute_host"] = self.destination_node
        migrated_server = self.create_openstacksdk_server(**kwargs)

        self.mock_connection.compute.get_server.side_effect = (
            server, server, server, migrated_server)

        # Migration will success as will transition from migrating to ACTIVE
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, self.destination_node
        )
        # Should succeed
        self.assertTrue(is_success)
        # It will sleep 2 times because it will be found as ACTIVE in
        # the second retry
        self.assertEqual(2, self.mock_sleep.call_count)
        # Verify all sleep calls used 5 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_retry_default(
            self, mock_migrate, mock_cinder):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "task_state": "migrating"
        }
        server = self.create_openstacksdk_server(**kwargs)

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        # Migration will timeout because host never changes
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, self.destination_node
        )
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With default migration_max_retries and migration_interval, should
        # sleep 5 seconds 180 times
        self.assertEqual(180, self.mock_sleep.call_count)
        # Verify all sleep calls used 5 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_retry_custom(
            self, mock_migrate, mock_cinder
    ):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "task_state": "migrating"
        }
        server = self.create_openstacksdk_server(**kwargs)

        # Set config value
        self.flags(migration_max_retries=20, migration_interval=1.5,
                   group='nova')

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        # Migration will timeout because host never changes
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, self.destination_node
        )
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With migration_max_retries and migration_interval, should sleep 20
        # times
        self.assertEqual(20, self.mock_sleep.call_count)

        # Verify sleep calls used 1.5 second
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 1.5)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_no_dest_retry_default(
        self, mock_migrate, mock_cinder
    ):
        """Test live_migrate with no destination uses config timeout"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_openstacksdk_server(**kwargs)

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        # Migration with no destination will timeout
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, None
        )
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With default migration_max_retries and migration_interval, should
        # sleep 180 times
        self.assertEqual(180, self.mock_sleep.call_count)

        # Verify all sleep calls used 5 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_no_dest_retry_custom(
            self, mock_migrate, mock_cinder):
        """Test live_migrate with no destination uses config timeout"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "compute_host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_openstacksdk_server(**kwargs)

        # Set config value
        self.flags(migration_max_retries=10, migration_interval=3,
                   group='nova')

        self.fake_nova_find_list(
            self.mock_connection, fake_find=server, fake_list=server
        )

        # Migration with no destination will timeout
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            nova_util, self.instance_uuid, None
        )
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With migration_max_retries and migration_interval, should sleep 10
        # times for 3 seconds
        self.assertEqual(10, self.mock_sleep.call_count)

        # Verify sleep calls used 3 second
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 3)

    def test_enable_service_nova_compute(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        svc = self.create_openstacksdk_service(id='nanjing', status='disabled')
        self.mock_connection.compute.services.return_value = [svc]
        nova_services = self.mock_connection.compute.enable_service
        svc_enabled = self.create_openstacksdk_service(id='nanjing')
        nova_services.return_value = svc_enabled

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertTrue(result)

        nova_services.assert_called_with('nanjing')

    def test_enable_service_missing_nova_compute(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        self.mock_connection.compute.services.return_value = []
        nova_services = self.mock_connection.compute.enable_service

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertFalse(result)

        nova_services.assert_not_called()

    def test_disable_service_missing_nova_compute(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        self.mock_connection.compute.services.return_value = []
        nova_services = self.mock_connection.compute.disable_service

        result = nova_util.disable_service_nova_compute('nanjing')
        self.assertFalse(result)

        nova_services.assert_not_called()

    def test_disable_service_nova_compute(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        svc = self.create_openstacksdk_service(id='nanjing')
        self.mock_connection.compute.services.return_value = [svc]
        nova_services = self.mock_connection.compute.disable_service
        svc_disabled = self.create_openstacksdk_service(
            id='nanjing', status='disabled'
        )
        nova_services.return_value = svc_disabled

        result = nova_util.disable_service_nova_compute(
            'nanjing', reason='test'
        )
        self.assertTrue(result)
        nova_services.assert_called_with('nanjing', disabled_reason='test')

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock()
        volume.id = kwargs.get('id', '45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba')
        volume.size = kwargs.get('size', '1')
        volume.status = kwargs.get('status', 'available')
        volume.snapshot_id = kwargs.get('snapshot_id', None)
        volume.availability_zone = kwargs.get('availability_zone', 'nova')
        return volume

    def test_wait_for_volume_status(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()

        # verify that the method will return True when the status of volume
        # is in the expected status.
        fake_volume_1 = self.fake_volume(status='in-use')
        nova_util.cinder.volumes.get.return_value = fake_volume_1
        result = nova_util.wait_for_volume_status(
            fake_volume_1,
            "in-use",
            timeout=2)
        self.assertTrue(result)

        # verify that the method will raise Exception when the status of
        # volume is not in the expected status.
        fake_volume_2 = self.fake_volume(status='fake-use')
        nova_util.cinder.volumes.get.return_value = fake_volume_2
        self.assertRaises(
            Exception,
            nova_util.wait_for_volume_status,
            fake_volume_1,
            "in-use",
            timeout=2)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_confirm_resize', autospec=True
    )
    def test_confirm_resize(self, mock_confirm_resize, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=instance, fake_list=None
        )

        server = nova_helper.Server.from_openstacksdk(instance)
        # verify that the method will return True when the status of instance
        # is not in the expected status.
        result = nova_util.confirm_resize(server, server.status)
        self.assertEqual(1, mock_confirm_resize.call_count)
        self.assertTrue(result)

        # verify that the method will return False when the status of instance
        # is not in the expected status.
        mock_confirm_resize.reset_mock()
        result = nova_util.confirm_resize(server, "fake_status")
        self.assertEqual(1, mock_confirm_resize.call_count)
        self.assertFalse(result)

    def test_get_compute_node_list(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        hypervisor1_id = utils.generate_uuid()
        hypervisor1_name = "fake_hypervisor_1"
        hypervisor1 = self.create_openstacksdk_hypervisor(
            id=hypervisor1_id, name=hypervisor1_name,
            hypervisor_type="QEMU"
        )

        hypervisor2_id = utils.generate_uuid()
        hypervisor2_name = "fake_ironic"
        hypervisor2 = self.create_openstacksdk_hypervisor(
            id=hypervisor2_id, name=hypervisor2_name,
            hypervisor_type="ironic"
        )

        self.mock_connection.compute.hypervisors.return_value = [
            hypervisor1, hypervisor2
        ]

        compute_nodes = nova_util.get_compute_node_list()

        # baremetal node should be removed
        self.assertEqual(1, len(compute_nodes))
        self.assertEqual(hypervisor1_name,
                         compute_nodes[0].hypervisor_hostname)

    def test_get_compute_node_list_with_ironic(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        hypervisor1_id = utils.generate_uuid()
        hypervisor1_name = "fake_hypervisor_1"
        hypervisor1 = self.create_openstacksdk_hypervisor(
            id=hypervisor1_id, name=hypervisor1_name,
            hypervisor_type="QEMU"
        )

        hypervisor2_id = utils.generate_uuid()
        hypervisor2_name = "fake_ironic"
        hypervisor2 = self.create_openstacksdk_hypervisor(
            id=hypervisor2_id, name=hypervisor2_name,
            hypervisor_type="ironic"
        )

        self.mock_connection.compute.hypervisors.return_value = [
            hypervisor1, hypervisor2
        ]

        compute_nodes = nova_util.get_compute_node_list(
            filter_ironic_nodes=False
        )

        # baremetal node should be included
        self.assertEqual(2, len(compute_nodes))
        self.assertEqual(hypervisor1_name,
                         compute_nodes[0].hypervisor_hostname)
        self.assertEqual(hypervisor2_name,
                         compute_nodes[1].hypervisor_hostname)

    def test_find_instance(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=instance, fake_list=None
        )

        result = nova_util.find_instance(self.instance_uuid)
        self.assertEqual(1, self.mock_connection.compute.get_server.call_count)
        self.mock_sleep.assert_not_called()
        self.assertEqual(
            nova_helper.Server.from_openstacksdk(instance), result)

    def test_find_instance_retries(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=instance, fake_list=None
        )
        self.mock_connection.compute.get_server.side_effect = [
            ksa_exc.ConnectionError("Connection failed"),
            instance
        ]

        result = nova_util.find_instance(self.instance_uuid)
        self.assertEqual(2, self.mock_connection.compute.get_server.call_count)
        self.assertEqual(1, self.mock_sleep.call_count)
        self.assertEqual(
            nova_helper.Server.from_openstacksdk(instance), result
        )

    def test_find_instance_retries_exhausts_retries(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        self.fake_nova_find_list(
            self.mock_connection, fake_find=instance, fake_list=None
        )
        err = ksa_exc.ConnectionError("Connection failed")
        self.mock_connection.compute.get_server.side_effect = err

        self.assertRaises(ksa_exc.ConnectionError,
                          nova_util.find_instance, self.instance_uuid)
        self.assertEqual(4, self.mock_connection.compute.get_server.call_count)
        self.assertEqual(3, self.mock_sleep.call_count)

    def test_nova_start_instance(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        nova_util._nova_start_instance(instance.id)
        self.mock_connection.compute.start_server.assert_called_once_with(
            instance.id
        )

    def test_nova_stop_instance(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        nova_util._nova_stop_instance(instance.id)
        self.mock_connection.compute.stop_server.assert_called_once_with(
            instance.id)

    def test_instance_resize(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        flavor_name = "m1.small"

        result = nova_util._instance_resize(instance, flavor_name)
        self.mock_connection.compute.resize_server.assert_called_once_with(
            instance, flavor_name
        )
        self.assertTrue(result)

    def test_instance_confirm_resize(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        nova_util._instance_confirm_resize(instance)
        self.mock_connection.compute.confirm_server_resize(instance)

    def test_instance_live_migrate(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        dest_hostname = "dest_hostname"
        nova_util._instance_live_migrate(instance, dest_hostname)
        migrate_method = self.mock_connection.compute.live_migrate_server
        migrate_method.assert_called_once_with(
            instance, host="dest_hostname", block_migration='auto'
        )

    def test_instance_migrate(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        dest_hostname = "dest_hostname"
        nova_util._instance_migrate(instance, dest_hostname)
        self.mock_connection.compute.migrate_server.assert_called_once_with(
            instance, host="dest_hostname"
        )

    def test_live_migration_abort(self, mock_cinder):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_openstacksdk_server(**kwargs)
        nova_util._live_migration_abort(instance.id, 1)
        self.mock_connection.compute.abort_server_migration.\
            assert_called_once_with(1, instance.id)

    def test_is_pinned_az_available_version_supported(self, mock_cinder):
        """Test is_pinned_az_available returns True for version >= 2.96."""
        nova_util = nova_helper.NovaHelper()
        CONF.set_override('api_version', '2.96', group='nova')

        result = nova_util.is_pinned_az_available()
        self.assertTrue(result)

    def test_is_pinned_az_available_version_higher(self, mock_cinder):
        """Test is_pinned_az_available returns True for version > 2.96."""
        nova_util = nova_helper.NovaHelper()
        CONF.set_override('api_version', '2.97', group='nova')

        result = nova_util.is_pinned_az_available()
        self.assertTrue(result)

    def test_is_pinned_az_available_version_not_supported(self, mock_cinder):
        """Test is_pinned_az_available returns False for version < 2.96."""
        nova_util = nova_helper.NovaHelper()
        CONF.set_override('api_version', '2.95', group='nova')

        result = nova_util.is_pinned_az_available()
        self.assertFalse(result)

    def test_is_pinned_az_available_version_much_lower(self, mock_cinder):
        """Test is_pinned_az_available returns False for older versions."""
        nova_util = nova_helper.NovaHelper()
        CONF.set_override('api_version', '2.53', group='nova')

        result = nova_util.is_pinned_az_available()
        self.assertFalse(result)

    def test_is_pinned_az_available_caching(self, mock_cinder):
        """Test is_pinned_az_available caches the result."""
        nova_util = nova_helper.NovaHelper()
        CONF.set_override('api_version', '2.96', group='nova')

        # Call the method multiple times
        result1 = nova_util.is_pinned_az_available()
        result2 = nova_util.is_pinned_az_available()

        # Both calls should return the same result
        self.assertTrue(result1)
        self.assertTrue(result2)

        # Verify that the result is cached
        self.assertIsNotNone(nova_util._is_pinned_az_available)

    def test_get_flavor_id_by_id(self, mock_cinder):
        """Test get_flavor_id returns id when flavor is found by ID."""
        nova_util = nova_helper.NovaHelper()
        flavor_id = 'flavor-123'
        flavor = self.create_openstacksdk_flavor(
            id=flavor_id, name='m1.small'
        )
        self.mock_connection.compute.get_flavor.return_value = flavor

        result = nova_util.get_flavor_id(flavor_id)

        self.assertEqual(flavor_id, result)
        self.mock_connection.compute.get_flavor.assert_called_once_with(
            flavor_id
        )

    def test_get_flavor_id_by_name(self, mock_cinder):
        """Test get_flavor_id returns id when flavor is found by name."""
        nova_util = nova_helper.NovaHelper()
        flavor_name = 'm1.small'
        flavor_id = 'flavor-123'
        flavor = self.create_openstacksdk_flavor(
            id=flavor_id, name=flavor_name
        )

        # First attempt to get by ID fails (NotFoundException)
        self.mock_connection.compute.get_flavor.side_effect = (
            sdk_exc.NotFoundException()
        )
        # get_flavor_list returns list with the flavor
        self.mock_connection.compute.flavors.return_value = [flavor]

        result = nova_util.get_flavor_id(flavor_name)

        self.assertEqual(flavor_id, result)
        self.mock_connection.compute.get_flavor.assert_called_once_with(
            flavor_name
        )
        self.mock_connection.compute.flavors.assert_called_once_with(
            is_public=None
        )

    def test_get_flavor_id_not_found_by_id_or_name(self, mock_cinder):
        """Test get_flavor_id raises exception when flavor is not found."""
        nova_util = nova_helper.NovaHelper()
        flavor_name = 'nonexistent-flavor'

        # First attempt to get by ID fails
        self.mock_connection.compute.get_flavor.side_effect = (
            sdk_exc.NotFoundException()
        )
        # get_flavor_list returns empty list
        self.mock_connection.compute.flavors.return_value = []

        self.assertRaisesRegex(
            exception.ComputeResourceNotFound,
            f"{flavor_name} of type Flavor",
            nova_util.get_flavor_id,
            flavor_name
        )

    def test_get_flavor_id_not_found_in_list(self, mock_cinder):
        """Test get_flavor_id when flavor name not in returned list."""
        nova_util = nova_helper.NovaHelper()
        flavor_name = 'm1.small'

        # First attempt to get by ID fails
        self.mock_connection.compute.get_flavor.side_effect = (
            sdk_exc.NotFoundException()
        )
        # get_flavor_list returns flavors but none match the name
        other_flavor = self.create_openstacksdk_flavor(
            id='other-id', name='m1.large'
        )
        self.mock_connection.compute.flavors.return_value = [other_flavor]

        self.assertRaisesRegex(
            exception.ComputeResourceNotFound,
            f"{flavor_name} of type Flavor",
            nova_util.get_flavor_id,
            flavor_name
        )

    def test_get_flavor_id_sdk_exception(self, mock_cinder):
        """Test get_flavor_id raises NovaClientError on SDK exception."""
        nova_util = nova_helper.NovaHelper()
        flavor_id = 'flavor-123'

        # SDK raises a generic exception
        self.mock_connection.compute.get_flavor.side_effect = (
            sdk_exc.SDKException("Connection error")
        )

        self.assertRaises(
            exception.NovaClientError,
            nova_util.get_flavor_id,
            flavor_id
        )

    def test_get_flavor_id_by_name_multiple_flavors(self, mock_cinder):
        """Test get_flavor_id finds correct flavor by name in list."""
        nova_util = nova_helper.NovaHelper()
        flavor_name = 'm1.medium'
        target_id = 'flavor-456'

        # Create multiple flavors
        flavor1 = self.create_openstacksdk_flavor(
            id='flavor-123', name='m1.small'
        )
        flavor2 = self.create_openstacksdk_flavor(
            id=target_id, name=flavor_name
        )
        flavor3 = self.create_openstacksdk_flavor(
            id='flavor-789', name='m1.large'
        )

        # First attempt to get by ID fails
        self.mock_connection.compute.get_flavor.side_effect = (
            sdk_exc.NotFoundException()
        )
        # get_flavor_list returns multiple flavors
        self.mock_connection.compute.flavors.return_value = [
            flavor1, flavor2, flavor3
        ]

        result = nova_util.get_flavor_id(flavor_name)

        self.assertEqual(target_id, result)


class TestNovaRetries(base.TestCase):
    """Test suite for the nova_retries decorator."""

    def setUp(self):
        super().setUp()
        self.mock_sleep = self.useFixture(
            fixtures.MockPatchObject(time, 'sleep')).mock

    def test_nova_retries_success_on_first_attempt(self):
        """Test that decorator returns result when function succeeds."""
        @nova_helper.nova_retries
        def mock_function():
            return "success"

        result = mock_function()
        self.assertEqual("success", result)
        self.mock_sleep.assert_not_called()

    def test_nova_retries_success_after_retries(self):
        """Test that decorator retries and succeeds after ConnectionError."""
        self.flags(http_retries=3, http_retry_interval=2, group='nova')

        call_count = {'count': 0}

        @nova_helper.nova_retries
        def mock_function():
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise ksa_exc.ConnectionError("Connection failed")
            return "success"

        result = mock_function()
        self.assertEqual("success", result)
        self.assertEqual(3, call_count['count'])
        # Should have slept 2 times (before retry 2 and 3)
        self.assertEqual(2, self.mock_sleep.call_count)
        # Verify sleep was called with correct interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 2)

    def test_nova_retries_exhausts_retries(self):
        """Test that decorator re-raises after exhausting retries."""
        self.flags(http_retries=3, http_retry_interval=1, group='nova')

        call_count = {'count': 0}

        @nova_helper.nova_retries
        def mock_function():
            call_count['count'] += 1
            raise ksa_exc.ConnectionError("Connection failed")

        self.assertRaises(ksa_exc.ConnectionError, mock_function)
        # Should have tried 3 times
        self.assertEqual(4, call_count['count'])
        # Should have slept 2 times (between attempts)
        self.assertEqual(3, self.mock_sleep.call_count)
        # Verify sleep was called with correct interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 1)

    def test_nova_retries_with_custom_retry_interval(self):
        """Test that decorator uses configured retry interval."""
        self.flags(http_retries=4, http_retry_interval=5, group='nova')

        call_count = {'count': 0}

        @nova_helper.nova_retries
        def mock_function():
            call_count['count'] += 1
            raise ksa_exc.ConnectionError("Connection failed")

        self.assertRaises(ksa_exc.ConnectionError, mock_function)
        # Should have tried 4 times
        self.assertEqual(5, call_count['count'])
        # Should have slept 3 times (between attempts)
        self.assertEqual(4, self.mock_sleep.call_count)
        # Verify sleep was called with 5 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    def test_nova_retries_with_function_args(self):
        """Test that decorator preserves function arguments and return."""
        @nova_helper.nova_retries
        def mock_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = mock_function("a", "b", kwarg1="c")
        self.assertEqual("a-b-c", result)
        self.mock_sleep.assert_not_called()

    def test_nova_retries_propagates_other_exceptions(self):
        """Test that decorator doesn't catch non-ConnectionError exception."""
        @nova_helper.nova_retries
        def mock_function():
            raise ValueError("Some other error")

        self.assertRaises(ValueError, mock_function)
        self.mock_sleep.assert_not_called()

    @mock.patch.object(nova_helper, 'LOG')
    def test_nova_retries_logging_on_retry(self, mock_log):
        """Test that decorator logs warnings during retries."""
        self.flags(http_retries=3, http_retry_interval=1, group='nova')

        call_count = {'count': 0}

        @nova_helper.nova_retries
        def mock_function():
            call_count['count'] += 1
            if call_count['count'] < 2:
                raise ksa_exc.ConnectionError("Connection failed")
            return "success"

        mock_function()

        # Should have logged warning about connection error
        self.assertTrue(mock_log.warning.called)
        # Check that retry message was logged
        warning_calls = [call for call in mock_log.warning.call_args_list
                         if 'Retrying connection' in str(call)]
        self.assertEqual(1, len(warning_calls))

    @mock.patch.object(nova_helper, 'LOG')
    def test_nova_retries_logging_on_final_failure(self, mock_log):
        """Test that decorator logs error when all retries are exhausted."""
        self.flags(http_retries=2, http_retry_interval=1, group='nova')

        @nova_helper.nova_retries
        def mock_function():
            raise ksa_exc.ConnectionError("Connection failed")

        self.assertRaises(ksa_exc.ConnectionError, mock_function)

        # Should have logged error about final failure
        self.assertTrue(mock_log.error.called)
        error_calls = [call for call in mock_log.error.call_args_list
                       if 'Failed to connect' in str(call)]
        self.assertEqual(1, len(error_calls))

    def test_nova_retries_single_retry_config(self):
        """Test decorator behavior with single retry configured."""
        self.flags(http_retries=1, http_retry_interval=1, group='nova')

        call_count = {'count': 0}

        @nova_helper.nova_retries
        def mock_function():
            call_count['count'] += 1
            raise ksa_exc.ConnectionError("Connection failed")

        self.assertRaises(ksa_exc.ConnectionError, mock_function)
        # Should have tried twice
        self.assertEqual(2, call_count['count'])
        # Should have slept once
        self.assertEqual(1, self.mock_sleep.call_count)


class TestServerWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the Server dataclass."""

    def test_server_post_init_valid_uuid(self):
        """Test Server accepts valid UUID."""
        valid_uuid = utils.generate_uuid()
        server = nova_helper.Server(
            uuid=valid_uuid,
            name='test-server',
            created='2026-01-01T00:00:00Z',
            host='compute-1',
            vm_state='active',
            task_state=None,
            power_state=1,
            status='ACTIVE',
            flavor={'id': '1'},
            tenant_id='tenant-123',
            locked=False,
            metadata={},
            availability_zone='nova',
            pinned_availability_zone=None
        )
        self.assertEqual(valid_uuid, server.uuid)

    def test_server_post_init_invalid_uuid(self):
        """Test Server raises InvalidUUID for invalid UUID."""
        self.assertRaises(
            exception.InvalidUUID,
            nova_helper.Server,
            uuid='not-a-valid-uuid',
            name='test-server',
            created='2026-01-01T00:00:00Z',
            host='compute-1',
            vm_state='active',
            task_state=None,
            power_state=1,
            status='ACTIVE',
            flavor={'id': '1'},
            tenant_id='tenant-123',
            locked=False,
            metadata={},
            availability_zone='nova',
            pinned_availability_zone=None
        )

    def test_server_from_openstacksdk_basic_properties(self):
        """Test Server.from_openstacksdk with basic properties."""
        server_id = utils.generate_uuid()
        sdk_server = self.create_openstacksdk_server(
            id=server_id,
            name='my-server',
            status='ACTIVE',
            created_at='2026-01-01T00:00:00Z',
            project_id='tenant-123',
            is_locked=True,
            metadata={'key': 'value'},
            pinned_availability_zone='az1'
        )

        wrapped = nova_helper.Server.from_openstacksdk(sdk_server)

        self.assertEqual(server_id, wrapped.uuid)
        self.assertEqual('my-server', wrapped.name)
        self.assertEqual('ACTIVE', wrapped.status)
        self.assertEqual('2026-01-01T00:00:00Z', wrapped.created)
        self.assertEqual('tenant-123', wrapped.tenant_id)
        self.assertTrue(wrapped.locked)
        self.assertEqual({'key': 'value'}, wrapped.metadata)
        self.assertEqual('az1', wrapped.pinned_availability_zone)

    def test_server_from_openstacksdk_extended_attributes(self):
        """Test Server.from_openstacksdk with extended attributes."""
        server_id = utils.generate_uuid()
        sdk_server = self.create_openstacksdk_server(
            id=server_id,
            compute_host='compute-1',
            vm_state='active',
            task_state=None,
            power_state=1,
            availability_zone='nova'
        )

        wrapped = nova_helper.Server.from_openstacksdk(sdk_server)

        self.assertEqual('compute-1', wrapped.host)
        self.assertEqual('active', wrapped.vm_state)
        self.assertIsNone(wrapped.task_state)
        self.assertEqual(1, wrapped.power_state)
        self.assertEqual('nova', wrapped.availability_zone)

    def test_server_from_openstacksdk_flavor(self):
        """Test Server.from_openstacksdk flavor property."""
        server_id = utils.generate_uuid()
        sdk_server = self.create_openstacksdk_server(
            id=server_id,
            flavor={'id': 'flavor-123', 'name': 'm1.small'}
        )

        wrapped = nova_helper.Server.from_openstacksdk(sdk_server)
        # OpenStackSDK converts flavor dict to Flavor object
        self.assertEqual('flavor-123', wrapped.flavor.id)
        self.assertEqual('m1.small', wrapped.flavor.name)


class TestHypervisorWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the Hypervisor dataclass."""

    def test_hypervisor_post_init_valid_uuid(self):
        """Test Hypervisor accepts valid UUID."""
        valid_uuid = utils.generate_uuid()
        hypervisor = nova_helper.Hypervisor(
            uuid=valid_uuid,
            hypervisor_hostname='compute-1',
            hypervisor_type='QEMU',
            state='up',
            status='enabled',
            vcpus=32,
            vcpus_used=8,
            memory_mb=65536,
            memory_mb_used=16384,
            local_gb=1000,
            local_gb_used=250,
            service_host='compute-1',
            service_id='svc-123',
            service_disabled_reason=None,
            servers=[]
        )
        self.assertEqual(valid_uuid, hypervisor.uuid)

    def test_hypervisor_post_init_invalid_uuid(self):
        """Test Hypervisor raises InvalidUUID for invalid UUID."""
        self.assertRaises(
            exception.InvalidUUID,
            nova_helper.Hypervisor,
            uuid='invalid-uuid-format',
            hypervisor_hostname='compute-1',
            hypervisor_type='QEMU',
            state='up',
            status='enabled',
            vcpus=32,
            vcpus_used=8,
            memory_mb=65536,
            memory_mb_used=16384,
            local_gb=1000,
            local_gb_used=250,
            service_host='compute-1',
            service_id='svc-123',
            service_disabled_reason=None,
            servers=[]
        )

    def test_hypervisor_servers_property(self):
        """Test Hypervisor dataclass servers property."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'

        # Create fake server objects with required attributes
        server1_id = utils.generate_uuid()
        server2_id = utils.generate_uuid()
        server1 = {
            'uuid': server1_id,
            'name': 'server1',
        }
        server2 = {
            'uuid': server2_id,
            'name': 'server2'
        }

        nova_hypervisor = self.create_openstacksdk_hypervisor(
            id=hypervisor_id,
            name=hostname,
            servers=[server1, server2]
        )

        wrapped = nova_helper.Hypervisor.from_openstacksdk(nova_hypervisor)

        # Servers should be wrapped as Server dataclasses
        result_servers = wrapped.servers
        self.assertEqual(2, len(result_servers))
        self.assertEqual(server1_id, result_servers[0]['uuid'])
        self.assertEqual(server2_id, result_servers[1]['uuid'])

    def test_hypervisor_from_openstacksdk_basic_properties(self):
        """Test Hypervisor.from_openstacksdk with basic properties."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'
        sdk_hypervisor = self.create_openstacksdk_hypervisor(
            id=hypervisor_id,
            name=hostname,
            hypervisor_type='QEMU',
            state='up',
            status='enabled',
            vcpus=32,
            vcpus_used=8,
            memory_size=65536,
            memory_used=16384,
            local_disk_size=1000,
            local_disk_used=250
        )

        wrapped = nova_helper.Hypervisor.from_openstacksdk(sdk_hypervisor)

        self.assertEqual(hypervisor_id, wrapped.uuid)
        self.assertEqual(hostname, wrapped.hypervisor_hostname)
        self.assertEqual('QEMU', wrapped.hypervisor_type)
        self.assertEqual('up', wrapped.state)
        self.assertEqual('enabled', wrapped.status)
        self.assertEqual(32, wrapped.vcpus)
        self.assertEqual(8, wrapped.vcpus_used)
        self.assertEqual(65536, wrapped.memory_mb)
        self.assertEqual(16384, wrapped.memory_mb_used)
        self.assertEqual(1000, wrapped.local_gb)
        self.assertEqual(250, wrapped.local_gb_used)

    def test_hypervisor_from_openstacksdk_service_properties(self):
        """Test Hypervisor.from_openstacksdk service properties."""
        hostname = 'compute-node-1'
        sdk_hypervisor = self.create_openstacksdk_hypervisor(
            id=utils.generate_uuid(),
            name=hostname,
            service_details={
                'host': hostname,
                'id': 42,
                'disabled_reason': 'maintenance'
            }
        )

        wrapped = nova_helper.Hypervisor.from_openstacksdk(sdk_hypervisor)

        self.assertEqual(hostname, wrapped.service_host)
        self.assertEqual(42, wrapped.service_id)
        self.assertEqual('maintenance', wrapped.service_disabled_reason)

    def test_hypervisor_from_openstacksdk_service_not_dict(self):
        """Test Hypervisor.from_openstacksdk when service is not a dict."""
        sdk_hypervisor = self.create_openstacksdk_hypervisor(
            id=utils.generate_uuid(),
            name='compute-node-1',
            service_details='not-a-dict'
        )

        wrapped = nova_helper.Hypervisor.from_openstacksdk(sdk_hypervisor)

        self.assertIsNone(wrapped.service_host)
        self.assertIsNone(wrapped.service_id)
        self.assertIsNone(wrapped.service_disabled_reason)

    def test_hypervisor_from_openstacksdk_servers_property(self):
        """Test Hypervisor.from_openstacksdk servers property."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'

        server1_id = utils.generate_uuid()
        server2_id = utils.generate_uuid()
        server1 = {
            'uuid': server1_id,
            'name': 'server1',
        }
        server2 = {
            'uuid': server2_id,
            'name': 'server2'
        }

        sdk_hypervisor = self.create_openstacksdk_hypervisor(
            id=hypervisor_id,
            name=hostname,
            servers=[server1, server2]
        )

        wrapped = nova_helper.Hypervisor.from_openstacksdk(sdk_hypervisor)

        result_servers = wrapped.servers
        self.assertEqual(2, len(result_servers))
        self.assertEqual(server1_id, result_servers[0]['uuid'])
        self.assertEqual(server2_id, result_servers[1]['uuid'])

    def test_hypervisor_from_openstacksdk_servers_none(self):
        """Test Hypervisor.from_openstacksdk when servers is None."""
        sdk_hypervisor = self.create_openstacksdk_hypervisor(
            id=utils.generate_uuid(),
            name='compute-node-1',
            servers=None
        )

        wrapped = nova_helper.Hypervisor.from_openstacksdk(sdk_hypervisor)
        self.assertEqual([], wrapped.servers)


class TestFlavorWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the Flavor dataclass."""

    def test_flavor_from_openstacksdk_basic_properties(self):
        """Test Flavor.from_openstacksdk with basic properties."""
        flavor_id = utils.generate_uuid()
        sdk_flavor = self.create_openstacksdk_flavor(
            id=flavor_id,
            name='m1.small',
            vcpus=2,
            ram=2048,
            disk=20,
            ephemeral=10,
            swap=512,
            is_public=True
        )

        wrapped = nova_helper.Flavor.from_openstacksdk(sdk_flavor)

        self.assertEqual(flavor_id, wrapped.id)
        self.assertEqual('m1.small', wrapped.flavor_name)
        self.assertEqual(2, wrapped.vcpus)
        self.assertEqual(2048, wrapped.ram)
        self.assertEqual(20, wrapped.disk)
        self.assertEqual(10, wrapped.ephemeral)
        self.assertEqual(512, wrapped.swap)
        self.assertTrue(wrapped.is_public)

    def test_flavor_from_openstacksdk_zero_swap(self):
        """Test Flavor.from_openstacksdk with zero swap."""
        flavor_id = utils.generate_uuid()
        sdk_flavor = self.create_openstacksdk_flavor(
            id=flavor_id,
            name='m1.noswap',
            swap=0
        )

        wrapped = nova_helper.Flavor.from_openstacksdk(sdk_flavor)
        self.assertEqual(0, wrapped.swap)

    def test_flavor_from_openstacksdk_private(self):
        """Test Flavor.from_openstacksdk with private flavor."""
        flavor_id = utils.generate_uuid()
        sdk_flavor = self.create_openstacksdk_flavor(
            id=flavor_id,
            name='m1.private',
            is_public=False
        )

        wrapped = nova_helper.Flavor.from_openstacksdk(sdk_flavor)
        self.assertFalse(wrapped.is_public)

    def test_flavor_from_openstacksdk_with_extra_specs(self):
        """Test Flavor.from_openstacksdk with extra_specs."""
        flavor_id = utils.generate_uuid()
        sdk_flavor = self.create_openstacksdk_flavor(
            id=flavor_id,
            name='m1.compute',
            extra_specs={'hw:cpu_policy': 'dedicated', 'hw:numa_nodes': '2'}
        )

        wrapped = nova_helper.Flavor.from_openstacksdk(sdk_flavor)

        self.assertEqual(
            {'hw:cpu_policy': 'dedicated', 'hw:numa_nodes': '2'},
            wrapped.extra_specs
        )

    def test_flavor_from_openstacksdk_without_extra_specs(self):
        """Test Flavor.from_openstacksdk without extra_specs."""
        flavor_id = utils.generate_uuid()
        sdk_flavor = self.create_openstacksdk_flavor(
            id=flavor_id,
            name='m1.basic'
        )

        wrapped = nova_helper.Flavor.from_openstacksdk(sdk_flavor)
        self.assertEqual({}, wrapped.extra_specs)


class TestAggregateWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the Aggregate dataclass."""

    def test_aggregate_from_openstacksdk_basic_properties(self):
        """Test Aggregate.from_openstacksdk with basic properties."""
        aggregate_id = utils.generate_uuid()
        sdk_aggregate = self.create_openstacksdk_aggregate(
            id=aggregate_id,
            name='test-aggregate',
            availability_zone='az1',
            hosts=['host1', 'host2', 'host3'],
            metadata={'ssd': 'true', 'gpu': 'nvidia'}
        )

        wrapped = nova_helper.Aggregate.from_openstacksdk(sdk_aggregate)

        self.assertEqual(aggregate_id, wrapped.id)
        self.assertEqual('test-aggregate', wrapped.name)
        self.assertEqual('az1', wrapped.availability_zone)
        self.assertEqual(['host1', 'host2', 'host3'], wrapped.hosts)
        self.assertEqual({'ssd': 'true', 'gpu': 'nvidia'}, wrapped.metadata)

    def test_aggregate_from_openstacksdk_no_az(self):
        """Test Aggregate.from_openstacksdk without availability zone."""
        aggregate_id = utils.generate_uuid()
        sdk_aggregate = self.create_openstacksdk_aggregate(
            id=aggregate_id,
            name='test-aggregate',
            availability_zone=None
        )

        wrapped = nova_helper.Aggregate.from_openstacksdk(sdk_aggregate)
        self.assertIsNone(wrapped.availability_zone)


class TestServiceWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the Service dataclass."""

    def test_service_post_init_valid_uuid(self):
        """Test Service accepts valid UUID."""
        valid_uuid = utils.generate_uuid()
        service = nova_helper.Service(
            uuid=valid_uuid,
            binary='nova-compute',
            host='compute-1',
            zone='nova',
            status='enabled',
            state='up',
            updated_at='2026-01-01T00:00:00Z',
            disabled_reason=None
        )
        self.assertEqual(valid_uuid, service.uuid)

    def test_service_post_init_invalid_uuid(self):
        """Test Service raises InvalidUUID for invalid UUID."""
        self.assertRaises(
            exception.InvalidUUID,
            nova_helper.Service,
            uuid='bad-uuid',
            binary='nova-compute',
            host='compute-1',
            zone='nova',
            status='enabled',
            state='up',
            updated_at='2026-01-01T00:00:00Z',
            disabled_reason=None
        )

    def test_service_from_openstacksdk_basic_properties(self):
        """Test Service.from_openstacksdk with basic properties."""
        service_id = utils.generate_uuid()
        sdk_service = self.create_openstacksdk_service(
            id=service_id,
            binary='nova-compute',
            host='compute-node-1',
            availability_zone='az1',
            status='enabled',
            state='up',
            updated_at='2026-01-09T12:00:00Z',
            disabled_reason=None
        )

        wrapped = nova_helper.Service.from_openstacksdk(sdk_service)

        self.assertEqual(service_id, wrapped.uuid)
        self.assertEqual('nova-compute', wrapped.binary)
        self.assertEqual('compute-node-1', wrapped.host)
        self.assertEqual('az1', wrapped.zone)
        self.assertEqual('enabled', wrapped.status)
        self.assertEqual('up', wrapped.state)
        self.assertEqual('2026-01-09T12:00:00Z', wrapped.updated_at)
        self.assertIsNone(wrapped.disabled_reason)

    def test_service_from_openstacksdk_disabled(self):
        """Test Service.from_openstacksdk with disabled service."""
        service_id = utils.generate_uuid()
        sdk_service = self.create_openstacksdk_service(
            id=service_id,
            status='disabled',
            state='down',
            disabled_reason='maintenance'
        )

        wrapped = nova_helper.Service.from_openstacksdk(sdk_service)

        self.assertEqual('disabled', wrapped.status)
        self.assertEqual('down', wrapped.state)
        self.assertEqual('maintenance', wrapped.disabled_reason)


class TestHandleNovaError(base.TestCase):
    """Test suite for the handle_nova_error decorator."""

    def test_handle_nova_error_returns_result_on_success(self):
        """Test that decorator returns result when function succeeds."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, instance_id):
            return "success"

        result = mock_function(None, "instance-123")
        self.assertEqual("success", result)

    def test_handle_nova_error_returns_none_on_not_found(self):
        """Test that decorator raises when NotFound is raised."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, instance_id):
            raise sdk_exc.NotFoundException()

        self.assertRaisesRegex(
            exception.ComputeResourceNotFound,
            "instance-123 of type Instance",
            mock_function, None, "instance-123"
        )

    @mock.patch.object(nova_helper, 'LOG', autospec=True)
    def test_handle_nova_error_logs_debug_message(self, mock_log):
        """Test that decorator logs debug message on NotFound."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, instance_id):
            raise sdk_exc.NotFoundException()

        self.assertRaisesRegex(
            exception.ComputeResourceNotFound,
            "instance-123 of type Instance",
            mock_function, None, "instance-123"
        )

        mock_log.debug.assert_called_once_with(
            "%s %s was not found", "Instance", "instance-123")

    def test_handle_nova_error_with_custom_resource_type(self):
        """Test that decorator uses custom resource type in log message."""
        @nova_helper.handle_nova_error("Flavor")
        def mock_function(self, flavor_id):
            raise sdk_exc.NotFoundException()

        with mock.patch.object(nova_helper, 'LOG', autospec=True) as mock_log:
            self.assertRaisesRegex(
                exception.ComputeResourceNotFound,
                "flavor-abc of type Flavor",
                mock_function, None, "flavor-abc"
            )
            mock_log.debug.assert_called_once_with(
                "%s %s was not found", "Flavor", "flavor-abc")

    def test_handle_nova_error_with_custom_id_arg_index(self):
        """Test that decorator uses custom id_arg_index."""
        @nova_helper.handle_nova_error("Aggregate", id_arg_index=2)
        def mock_function(self, other_arg, aggregate_id):
            raise sdk_exc.NotFoundException()

        with mock.patch.object(nova_helper, 'LOG', autospec=True) as mock_log:
            self.assertRaisesRegex(
                exception.ComputeResourceNotFound,
                "agg-123 of type Aggregate",
                mock_function, None, "other", "agg-123"
            )
            mock_log.debug.assert_called_once_with(
                "%s %s was not found", "Aggregate", "agg-123")

    def test_handle_nova_error_logs_unknown_when_no_id_arg(self):
        """Test that decorator logs 'unknown' when id arg is missing."""
        @nova_helper.handle_nova_error("Instance", id_arg_index=5)
        def mock_function(self, instance_id):
            raise sdk_exc.NotFoundException()

        with mock.patch.object(nova_helper, 'LOG', autospec=True) as mock_log:
            self.assertRaisesRegex(
                exception.ComputeResourceNotFound,
                "unknown of type Instance",
                mock_function, None, "instance-123"
            )
            mock_log.debug.assert_called_once_with(
                "%s %s was not found", "Instance", "unknown")

    def test_handle_nova_error_propagates_non_nova_exceptions(self):
        """Test that decorator doesn't catch non-novaclient exceptions."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, instance_id):
            raise ValueError("Some other error")

        self.assertRaises(ValueError, mock_function, None, "instance-123")

    def test_handle_nova_error_reraises_client_exception(self):
        """Test that ClientException is re-raised as NovaClientError."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, instance_id):
            raise sdk_exc.SDKException("Nova error")

        self.assertRaises(
            exception.NovaClientError, mock_function, None, "instance-123")

    def test_handle_nova_error_logs_client_exception(self):
        """Test that ClientException is logged before re-raising."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, instance_id):
            raise sdk_exc.SDKException("Nova error")

        self.assertRaises(
            exception.NovaClientError, mock_function, None, "instance-123")

    def test_handle_nova_error_preserves_function_args(self):
        """Test that decorator preserves function arguments and return."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, arg1, kwarg1=None):
            return f"{arg1}-{kwarg1}"

        result = mock_function(None, "a", kwarg1="b")
        self.assertEqual("a-b", result)

    def test_handle_nova_error_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @nova_helper.handle_nova_error("Instance")
        def my_function(self, instance_id):
            return "result"

        self.assertEqual("my_function", my_function.__name__)


class TestServerMigrationWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the ServerMigration dataclass."""

    def test_migration_from_openstacksdk_basic_properties(self):
        """Test ServerMigration.from_openstacksdk with basic properties."""
        migration_id = utils.generate_uuid()
        sdk_migration = self.create_openstacksdk_migration(
            id=migration_id
        )

        wrapped = nova_helper.ServerMigration.from_openstacksdk(sdk_migration)
        self.assertEqual(migration_id, wrapped.id)

    def test_migration_equality_from_openstacksdk(self):
        """Test ServerMigration dataclass equality comparison."""
        migration_id1 = utils.generate_uuid()
        migration_id2 = utils.generate_uuid()

        mig1a = nova_helper.ServerMigration.from_openstacksdk(
            self.create_openstacksdk_migration(id=migration_id1))
        mig1b = nova_helper.ServerMigration.from_openstacksdk(
            self.create_openstacksdk_migration(id=migration_id1))
        mig2 = nova_helper.ServerMigration.from_openstacksdk(
            self.create_openstacksdk_migration(id=migration_id2))

        # Same ID and attributes should be equal
        self.assertEqual(mig1a, mig1b)

        # Different ID should not be equal
        self.assertNotEqual(mig1a, mig2)

        # Compare with non-ServerMigration object
        self.assertNotEqual(mig1a, "not-a-migration")


@mock.patch.object(clients.OpenStackClients, 'cinder', autospec=True)
class TestNovaHelperConfigOverrides(base.TestCase):
    """Test suite for the NovaHelper config override functionality.

    Tests the deprecated config migration from [nova_client] to [nova] group.
    """

    def setUp(self):
        super().setUp()
        self.useFixture(
            fixtures.MockPatch("watcher.common.clients.get_sdk_connection")
        )

    def test_endpoint_type_override_public_url(self, mock_cinder):
        """Test endpoint_type publicURL is converted to public."""
        self.flags(endpoint_type='publicURL', group='nova_client')

        nova_helper.NovaHelper()

        self.assertEqual(['public'], CONF.nova.valid_interfaces)

    def test_endpoint_type_override_internal_url(self, mock_cinder):
        """Test endpoint_type internalURL is converted to internal."""
        self.flags(endpoint_type='internalURL', group='nova_client')

        nova_helper.NovaHelper()

        self.assertEqual(['internal'], CONF.nova.valid_interfaces)

    def test_endpoint_type_override_admin_url(self, mock_cinder):
        """Test endpoint_type adminURL is converted to admin."""
        self.flags(endpoint_type='adminURL', group='nova_client')

        nova_helper.NovaHelper()

        self.assertEqual(['admin'], CONF.nova.valid_interfaces)

    def test_endpoint_type_override_without_url_suffix(self, mock_cinder):
        """Test endpoint_type without URL suffix is preserved."""
        self.flags(endpoint_type='public', group='nova_client')

        nova_helper.NovaHelper()

        self.assertEqual(['public'], CONF.nova.valid_interfaces)

    def test_endpoint_type_override_internal_without_suffix(self, mock_cinder):
        """Test endpoint_type internal without suffix is preserved."""
        self.flags(endpoint_type='internal', group='nova_client')

        nova_helper.NovaHelper()

        self.assertEqual(['internal'], CONF.nova.valid_interfaces)

    def test_endpoint_type_override_admin_without_suffix(self, mock_cinder):
        """Test endpoint_type admin without suffix is preserved."""
        self.flags(endpoint_type='admin', group='nova_client')

        nova_helper.NovaHelper()

        self.assertEqual(['admin'], CONF.nova.valid_interfaces)
