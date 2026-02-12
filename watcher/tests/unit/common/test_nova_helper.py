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
from novaclient import api_versions

import novaclient.exceptions as nvexceptions
from novaclient.v2 import flavors
from novaclient.v2 import hypervisors
from novaclient.v2 import servers

from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import utils
from watcher import conf
from watcher.tests.unit import base

CONF = conf.CONF


@mock.patch.object(clients.OpenStackClients, 'nova')
@mock.patch.object(clients.OpenStackClients, 'cinder')
class TestNovaHelper(base.TestCase):

    def setUp(self):
        super().setUp()
        self.instance_uuid = "fb5311b7-37f3-457e-9cde-6494a3c59bfe"
        self.source_node = "ldev-indeedsrv005"
        self.destination_node = "ldev-indeedsrv006"
        self.flavor_name = "x1"
        self.mock_sleep = self.useFixture(
            fixtures.MockPatchObject(time, 'sleep')).mock

    @staticmethod
    def fake_server(*args, **kwargs):
        instance_info = {
            'id': args[0],
            'name': 'fake_instance',
            'status': 'ACTIVE',
        }
        instance_info.update(kwargs)

        return servers.Server(servers.ServerManager, info=instance_info)

    @staticmethod
    def fake_hypervisor(*args, **kwargs):
        hypervisor_info = {
            'id': args[0],
            'hypervisor_hostname': args[1],
            'hypervisor_type': kwargs.pop('hypervisor_type', 'QEMU'),
            'service': {
                'host': args[1]
            }
        }
        hypervisor_info.update(kwargs)

        return hypervisors.Hypervisor(
            hypervisors.HypervisorManager, info=hypervisor_info)

    @staticmethod
    def fake_migration(*args, **kwargs):
        migration = mock.MagicMock()
        migration.id = args[0]
        return migration

    @staticmethod
    def fake_nova_find_list(nova_util, fake_find=None, fake_list=None):
        nova_util.nova.servers.get.return_value = fake_find
        if fake_list is None:
            nova_util.nova.servers.list.return_value = []
        # check if fake_list is a list and return it
        elif isinstance(fake_list, list):
            nova_util.nova.servers.list.return_value = fake_list
        else:
            nova_util.nova.servers.list.return_value = [fake_list]

    @staticmethod
    def fake_nova_hypervisor_list(nova_util, fake_find=None, fake_list=None):
        nova_util.nova.hypervisors.get.return_value = fake_find
        nova_util.nova.hypervisors.list.return_value = fake_list

    @staticmethod
    def fake_nova_migration_list(nova_util, fake_list=None):
        if fake_list is None:
            nova_util.nova.server_migrations.list.return_value = None
        else:
            nova_util.nova.server_migration.list.return_value = [fake_list]

    def test_get_compute_node_by_hostname(
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        hypervisor_id = utils.generate_uuid()
        hypervisor_name = "fake_hypervisor_1"
        hypervisor = self.fake_hypervisor(hypervisor_id, hypervisor_name)
        nova_util.nova.hypervisors.search.return_value = [hypervisor]
        # verify that the compute node can be obtained normally by name
        self.assertEqual(
            nova_util.get_compute_node_by_hostname(hypervisor_name),
            hypervisor)

        # verify that getting the compute node with the wrong name
        # will throw an exception.
        self.assertRaises(
            exception.ComputeNodeNotFound,
            nova_util.get_compute_node_by_hostname,
            "exception_hypervisor_1")

        # verify that when the result of getting the compute node is empty
        # will throw an exception.
        nova_util.nova.hypervisors.search.return_value = []
        self.assertRaises(
            exception.ComputeNodeNotFound,
            nova_util.get_compute_node_by_hostname,
            hypervisor_name)

    def test_get_compute_node_by_hostname_multiple_matches(self, *mocks):
        # Tests a scenario where get_compute_node_by_name returns multiple
        # hypervisors and we have to pick the exact match based on the given
        # compute service hostname.
        nova_util = nova_helper.NovaHelper()
        nodes = []
        # compute1 is a substring of compute10 to trigger the fuzzy match.
        for hostname in ('compute1', 'compute10'):
            node = mock.MagicMock()
            node.id = utils.generate_uuid()
            node.hypervisor_hostname = hostname
            node.service = {'host': hostname}
            nodes.append(node)
        # We should get back exact matches based on the service host.
        nova_util.nova.hypervisors.search.return_value = nodes
        for index, name in enumerate(['compute1', 'compute10']):
            result = nova_util.get_compute_node_by_hostname(name)
            self.assertIs(nodes[index], result)

    def test_get_compute_node_by_uuid(
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        hypervisor_id = utils.generate_uuid()
        hypervisor_name = "fake_hypervisor_1"
        hypervisor = self.fake_hypervisor(hypervisor_id, hypervisor_name)
        nova_util.nova.hypervisors.get.return_value = hypervisor
        # verify that the compute node can be obtained normally by id
        self.assertEqual(
            nova_util.get_compute_node_by_uuid(hypervisor_id),
            hypervisor)

    def test_get_instance_list(self, *args):
        nova_util = nova_helper.NovaHelper()
        # Call it once with no filters.
        with mock.patch.object(nova_util, 'nova') as nova_mock:
            result = nova_util.get_instance_list()
            nova_mock.servers.list.assert_called_once_with(
                search_opts={'all_tenants': True}, marker=None, limit=-1)
            self.assertIs(result, nova_mock.servers.list.return_value)
        # Call it again with filters.
        with mock.patch.object(nova_util, 'nova') as nova_mock:
            result = nova_util.get_instance_list(filters={'host': 'fake-host'})
            nova_mock.servers.list.assert_called_once_with(
                search_opts={'all_tenants': True, 'host': 'fake-host'},
                marker=None, limit=-1)
            self.assertIs(result, nova_mock.servers.list.return_value)

    def test_stop_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        # verify that the method will return True when stopped
        kwargs = {
            "OS-EXT-STS:vm_state": "stopped"
        }
        server = self.fake_server(instance_id, **kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        result = nova_util.stop_instance(instance_id)
        self.assertTrue(result)

        # verify that the method will return False when active
        kwargs = {
            "OS-EXT-STS:vm_state": "active"
        }
        server = self.fake_server(instance_id, **kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)

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
        nova_util.nova.servers.get.return_value = None
        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

    def test_start_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        # verify that the method will return True when active
        kwargs = {
            "OS-EXT-STS:vm_state": "active"
        }
        server = self.fake_server(instance_id, **kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        result = nova_util.start_instance(instance_id)
        self.assertTrue(result)

        # verify that the method will return False when stopped
        kwargs = {
            "OS-EXT-STS:vm_state": "stopped"
        }
        server = self.fake_server(instance_id, **kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)

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
        nova_util.nova.servers.get.return_value = None
        result = nova_util.start_instance(instance_id)
        self.assertFalse(result)

    @mock.patch.object(servers.Server, 'resize', autospec=True)
    @mock.patch.object(servers.Server, 'confirm_resize', autospec=True)
    def test_resize_instance(self, mock_confirm_resize, mock_resize,
                             mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "status": "VERIFY_RESIZE",
            "OS-EXT-STS:vm_state": "resized"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        flavor = flavors.Flavor(flavors.FlavorManager, info={
                                'id': self.flavor_name,
                                'name': self.flavor_name})
        nova_util.nova.flavors.get.return_value = flavor
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertTrue(is_success)
        mock_resize.assert_called_once_with(server, flavor=self.flavor_name)
        self.assertEqual(1, mock_confirm_resize.call_count)

    @mock.patch.object(servers.Server, 'resize', autospec=True)
    def test_resize_instance_wrong_status(self, mock_resize,
                                          mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {"status": "SOMETHING_ELSE",
                  "OS-EXT-STS:vm_state": "resizing"}
        server = self.fake_server(self.instance_uuid, **kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        flavor = flavors.Flavor(flavors.FlavorManager, info={
                                'id': self.flavor_name,
                                'name': self.flavor_name})
        nova_util.nova.flavors.get.return_value = flavor
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertFalse(is_success)
        mock_resize.assert_called_once_with(server, flavor=self.flavor_name)

    @mock.patch.object(servers.Server, 'confirm_resize', autospec=True)
    @mock.patch.object(servers.Server, 'resize', autospec=True)
    def test_watcher_resize_instance_retry_success(
            self, mock_resize, mock_confirm_resize, mock_cinder, mock_nova):
        """Test that resize_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {"status": "RESIZING", "OS-EXT-STS:vm_state": "resizing"}
        server = self.fake_server(self.instance_uuid, **kwargs)

        kwargs = {"status": "VERIFY_RESIZE", "OS-EXT-STS:vm_state": "resized"}
        resized_server = self.fake_server(self.instance_uuid, **kwargs)

        # This means instance will be found as VERIFY_RESIZE in second retry
        nova_util.nova.servers.get.side_effect = (server, server,
                                                  resized_server)

        mock_confirm_resize.return_value = True

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

    @mock.patch.object(servers.Server, 'resize', autospec=True)
    def test_watcher_resize_instance_retry_default(
            self, mock_resize, mock_cinder, mock_nova):
        """Test that resize_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {"status": "RESIZING", "OS-EXT-STS:vm_state": "resizing"}
        self.fake_server(self.instance_uuid, **kwargs)

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

    def test_watcher_resize_instance_retry_custom(
            self, mock_cinder, mock_nova):
        """Test that watcher_non_live_migrate respects explicit retry value"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "status": "RESIZING",
            "OS-EXT-STS:vm_state": "resizing"
        }
        self.fake_server(self.instance_uuid, **kwargs)

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

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance(self, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.destination_node
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

        # verify that the method will return False when the instance does
        # not exist.
        self.fake_nova_find_list(nova_util, fake_find=None, fake_list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

        # verify that the method will return False when the instance status
        # is in other cases.
        server.status = 'fake_status'
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )
        self.assertFalse(is_success)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance_with_task_state(
            self, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": ""
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.mock_sleep.assert_not_called()

        kwargs["OS-EXT-STS:task_state"] = 'migrating'
        server = self.fake_server(self.instance_uuid, **kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.mock_sleep.assert_called_with(5)
        mock_migrate.assert_called_with(server, host=self.destination_node)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance_no_destination_node(
            self, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.destination_node,
            "status": "ACTIVE"
        }
        migrated_server = self.fake_server(self.instance_uuid, **kwargs)

        nova_util.nova.servers.get.side_effect = (
            server, server, migrated_server)

        # Migration will success as will transition from migrating to ACTIVE
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(server, host=None)
        # Should succeed
        self.assertTrue(is_success)

    def test_watcher_non_live_migrate_instance_not_found(
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        self.fake_nova_find_list(nova_util, fake_find=None, fake_list=None)

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node)

        self.assertFalse(is_success)

    def test_abort_live_migrate_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": None
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        migration = self.fake_migration(2)
        self.fake_nova_migration_list(nova_util, fake_list=migration)

        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        self.assertTrue(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.destination_node,
            "OS-EXT-STS:task_state": None
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

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
            "OS-EXT-STS:task_state": "fake_task_state",
            "OS-EXT-SRV-ATTR:host": self.destination_node
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        self.fake_nova_migration_list(nova_util, fake_list=None)
        self.assertFalse(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

    @mock.patch.object(servers.Server, 'migrate', autospec=True)
    @mock.patch.object(nova_helper.NovaHelper, 'confirm_resize', autospec=True)
    def test_non_live_migrate_instance_no_destination_node(
            self, mock_confirm_resize, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.destination_node,
            "status": "VERIFY_RESIZE"
        }
        migrated_server = self.fake_server(self.instance_uuid, **kwargs)

        nova_util.nova.servers.get.side_effect = (
            server, server, server, migrated_server)

        self.destination_node = None
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, None
        )
        mock_migrate.assert_called_once_with(server, host=None)
        self.assertEqual(1, mock_confirm_resize.call_count)
        self.assertTrue(is_success)

    @mock.patch.object(nova_helper.NovaHelper, 'confirm_resize', autospec=True)
    @mock.patch.object(servers.Server, 'migrate', autospec=True)
    def test_watcher_non_live_migrate_instance_retry_success(
            self, mock_migrate, mock_confirm_resize, mock_cinder, mock_nova):
        """Test that watcher_non_live_migrate uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        server.status = 'MIGRATING'  # Never reaches ACTIVE

        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.destination_node
        }
        verify_server = self.fake_server(self.instance_uuid, **kwargs)
        verify_server.status = 'VERIFY_RESIZE'

        # This means instance will be found as VERIFY_RESIZE in second retry
        nova_util.nova.servers.get.side_effect = (server, server, server,
                                                  verify_server)

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
            server, host=self.destination_node)
        # Should succeed
        self.assertTrue(is_success)
        # It will sleep 2 times because it will be found as VERIFY_RESIZE in
        # the second retry
        self.assertEqual(2, self.mock_sleep.call_count)
        # Verify all sleep calls used 4 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 4)

    @mock.patch.object(servers.Server, 'migrate', autospec=True)
    def test_watcher_non_live_migrate_instance_retry_default(
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that watcher_non_live_migrate uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

        # Migration will timeout because status never changes
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            server, host=self.destination_node)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With default migration_max_retries and migration_interval, should
        # sleep 180 times for 5 seconds
        self.assertEqual(180, self.mock_sleep.call_count)
        # Verify sleep calls used 5 second
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(servers.Server, 'migrate', autospec=True)
    def test_watcher_non_live_migrate_instance_retry_custom(
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that watcher_non_live_migrate respects explicit retry value"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node
        }
        server = self.fake_server(self.instance_uuid, **kwargs)
        server.status = 'MIGRATING'  # Never reaches ACTIVE

        # Set config to a custom values to ensure custom values are used
        self.flags(migration_max_retries=10, migration_interval=3,
                   group='nova')

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            server, host=self.destination_node)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # It should sleep migration_max_retries times with migration_interval
        # seconds
        self.assertEqual(10, self.mock_sleep.call_count)
        # Verify all sleep calls used migration_interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 3)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance_retry_default_success(
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        kwargs["OS-EXT-SRV-ATTR:host"] = self.destination_node
        migrated_server = self.fake_server(self.instance_uuid, **kwargs)

        nova_util.nova.servers.get.side_effect = (
            server, server, server, migrated_server)

        # Migration will success as will transition from migrating to ACTIVE
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            server, host=self.destination_node)
        # Should succeed
        self.assertTrue(is_success)
        # It will sleep 2 times because it will be found as ACTIVE in
        # the second retry
        self.assertEqual(2, self.mock_sleep.call_count)
        # Verify all sleep calls used 5 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance_retry_default(
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

        # Migration will timeout because host never changes
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            server, host=self.destination_node)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With default migration_max_retries and migration_interval, should
        # sleep 5 seconds 180 times
        self.assertEqual(180, self.mock_sleep.call_count)
        # Verify all sleep calls used 5 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance_retry_custom(
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        # Set config value
        self.flags(migration_max_retries=20, migration_interval=1.5,
                   group='nova')

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

        # Migration will timeout because host never changes
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(
            server, host=self.destination_node)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With migration_max_retries and migration_interval, should sleep 20
        # times
        self.assertEqual(20, self.mock_sleep.call_count)

        # Verify sleep calls used 1.5 second
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 1.5)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance_no_dest_retry_default(
            self, mock_migrate, mock_cinder, mock_nova):
        """Test live_migrate with no destination uses config timeout"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

        # Migration with no destination will timeout
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(server, host=None)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With default migration_max_retries and migration_interval, should
        # sleep 180 times
        self.assertEqual(180, self.mock_sleep.call_count)

        # Verify all sleep calls used 5 second interval
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 5)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_live_migrate_instance_no_dest_retry_custom(
            self, mock_migrate, mock_cinder, mock_nova):
        """Test live_migrate with no destination uses config timeout"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.fake_server(self.instance_uuid, **kwargs)

        # Set config value
        self.flags(migration_max_retries=10, migration_interval=3,
                   group='nova')

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

        # Migration with no destination will timeout
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )

        # Should call once to migrate the instance
        mock_migrate.assert_called_once_with(server, host=None)
        # Should fail due to timeout
        self.assertFalse(is_success)
        # With migration_max_retries and migration_interval, should sleep 10
        # times for 3 seconds
        self.assertEqual(10, self.mock_sleep.call_count)

        # Verify sleep calls used 3 second
        for call in self.mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 3)

    def test_enable_service_nova_compute(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_services = nova_util.nova.services
        nova_services.enable.return_value = mock.MagicMock(
            status='enabled')

        CONF.set_override('api_version', '2.52', group='nova_client')

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertTrue(result)

        nova_util.nova.services.enable.assert_called_with(
            host='nanjing', binary='nova-compute')

        nova_services.enable.return_value = mock.MagicMock(
            status='disabled')

        CONF.set_override('api_version', '2.56', group='nova_client')

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertFalse(result)

        nova_util.nova.services.enable.assert_called_with(
            service_uuid=mock.ANY)

    def test_disable_service_nova_compute(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_services = nova_util.nova.services
        nova_services.disable_log_reason.return_value = mock.MagicMock(
            status='enabled')

        CONF.set_override('api_version', '2.52', group='nova_client')

        result = nova_util.disable_service_nova_compute(
            'nanjing', reason='test')
        self.assertFalse(result)

        nova_services.disable_log_reason.assert_called_with(
            host='nanjing', binary='nova-compute', reason='test')

        nova_services.disable_log_reason.return_value = mock.MagicMock(
            status='disabled')

        CONF.set_override('api_version', '2.56', group='nova_client')

        result = nova_util.disable_service_nova_compute(
            'nanjing', reason='test2')
        self.assertTrue(result)

        nova_util.nova.services.disable_log_reason.assert_called_with(
            service_uuid=mock.ANY, reason='test2')

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock()
        volume.id = kwargs.get('id', '45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba')
        volume.size = kwargs.get('size', '1')
        volume.status = kwargs.get('status', 'available')
        volume.snapshot_id = kwargs.get('snapshot_id', None)
        volume.availability_zone = kwargs.get('availability_zone', 'nova')
        return volume

    def test_wait_for_volume_status(self, mock_cinder, mock_nova):
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

    @mock.patch.object(api_versions, 'APIVersion', mock.MagicMock())
    def test_check_nova_api_version(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()

        # verify that the method will return True when the version of nova_api
        # is supported.
        result = nova_util._check_nova_api_version(nova_util.nova, "2.56")
        self.assertTrue(result)

        # verify that the method will return False when the version of nova_api
        # is not supported.
        side_effect = nvexceptions.UnsupportedVersion()
        api_versions.discover_version = mock.MagicMock(
            side_effect=side_effect)
        result = nova_util._check_nova_api_version(nova_util.nova, "2.56")
        self.assertFalse(result)

    @mock.patch.object(servers.Server, 'confirm_resize', autospec=True)
    def test_confirm_resize(self, mock_confirm_resize, mock_cinder,
                            mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, fake_find=instance,
                                 fake_list=None)

        # verify that the method will return True when the status of instance
        # is not in the expected status.
        result = nova_util.confirm_resize(instance, instance.status)
        self.assertEqual(1, mock_confirm_resize.call_count)
        self.assertTrue(result)

        # verify that the method will return False when the status of instance
        # is not in the expected status.
        mock_confirm_resize.reset_mock()
        result = nova_util.confirm_resize(instance, "fake_status")
        self.assertEqual(1, mock_confirm_resize.call_count)
        self.assertFalse(result)

    def test_get_compute_node_list(
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        hypervisor1_id = utils.generate_uuid()
        hypervisor1_name = "fake_hypervisor_1"
        hypervisor1 = self.fake_hypervisor(
            hypervisor1_id, hypervisor1_name, hypervisor_type="QEMU")

        hypervisor2_id = utils.generate_uuid()
        hypervisor2_name = "fake_ironic"
        hypervisor2 = self.fake_hypervisor(
            hypervisor2_id, hypervisor2_name, hypervisor_type="ironic")

        nova_util.nova.hypervisors.list.return_value = [hypervisor1,
                                                        hypervisor2]

        compute_nodes = nova_util.get_compute_node_list()

        # baremetal node should be removed
        self.assertEqual(1, len(compute_nodes))
        self.assertEqual(hypervisor1_name,
                         compute_nodes[0].hypervisor_hostname)

    def test_find_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, fake_find=instance,
                                 fake_list=None)
        nova_util.nova.servers.get.return_value = instance

        result = nova_util.find_instance(self.instance_uuid)
        self.assertEqual(1, nova_util.nova.servers.get.call_count)
        self.mock_sleep.assert_not_called()
        self.assertEqual(instance, result)

    def test_find_instance_retries(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, fake_find=instance,
                                 fake_list=None)
        nova_util.nova.servers.get.side_effect = [
            ksa_exc.ConnectionError("Connection failed"),
            instance
        ]

        result = nova_util.find_instance(self.instance_uuid)
        self.assertEqual(2, nova_util.nova.servers.get.call_count)
        self.assertEqual(1, self.mock_sleep.call_count)
        self.assertEqual(instance, result)

    def test_find_instance_retries_exhausts_retries(self, mock_cinder,
                                                    mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, fake_find=instance,
                                 fake_list=None)
        nova_util.nova.servers.get.side_effect = ksa_exc.ConnectionError(
            "Connection failed")

        self.assertRaises(ksa_exc.ConnectionError,
                          nova_util.find_instance, self.instance_uuid)
        self.assertEqual(4, nova_util.nova.servers.get.call_count)
        self.assertEqual(3, self.mock_sleep.call_count)

    def test_nova_start_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        nova_util.nova_start_instance(instance.id)
        nova_util.nova.servers.start.assert_called_once_with(instance.id)

    def test_nova_stop_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        nova_util.nova_stop_instance(instance.id)
        nova_util.nova.servers.stop.assert_called_once_with(instance.id)

    @mock.patch.object(servers.Server, 'resize', autospec=True)
    def test_instance_resize(self, mock_resize, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        flavor_name = "m1.small"

        result = nova_util.instance_resize(instance, flavor_name)
        mock_resize.assert_called_once_with(instance, flavor=flavor_name)
        self.assertTrue(result)

    @mock.patch.object(servers.Server, 'confirm_resize', autospec=True)
    def test_instance_confirm_resize(self, mock_confirm_resize, mock_cinder,
                                     mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        nova_util.instance_confirm_resize(instance)
        mock_confirm_resize.assert_called_once_with(instance)

    @mock.patch.object(servers.Server, 'live_migrate', autospec=True)
    def test_instance_live_migrate(self, mock_live_migrate, mock_cinder,
                                   mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        dest_hostname = "dest_hostname"
        nova_util.instance_live_migrate(instance, dest_hostname)
        mock_live_migrate.assert_called_once_with(
            instance, host="dest_hostname")

    @mock.patch.object(servers.Server, 'migrate', autospec=True)
    def test_instance_migrate(self, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        dest_hostname = "dest_hostname"
        nova_util.instance_migrate(instance, dest_hostname)
        mock_migrate.assert_called_once_with(instance, host="dest_hostname")

    def test_live_migration_abort(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        nova_util.live_migration_abort(instance.id, 1)
        nova_util.nova.server_migrations.live_migration_abort.\
            assert_called_once_with(server=instance.id, migration=1)


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


class TestServerWrapper(base.TestCase):
    """Test suite for the Server dataclass."""

    @staticmethod
    def create_nova_server(server_id, **kwargs):
        """Create a real novaclient Server object.

        :param server_id: server UUID
        :param kwargs: additional server attributes
        :returns: novaclient.v2.servers.Server object
        """
        server_info = {
            'id': server_id,
            'name': kwargs.pop('name', 'test-server'),
            'status': kwargs.pop('status', 'ACTIVE'),
            'created': kwargs.pop('created', '2026-01-09T12:00:00Z'),
            'tenant_id': kwargs.pop('tenant_id', 'test-tenant-id'),
            'locked': kwargs.pop('locked', False),
            'metadata': kwargs.pop('metadata', {}),
            'flavor': kwargs.pop('flavor', {'id': 'flavor-1'}),
            'pinned_availability_zone': kwargs.pop(
                'pinned_availability_zone', None),
        }
        server_info.update(kwargs)
        return servers.Server(servers.ServerManager, info=server_info)

    def test_server_basic_properties(self):
        """Test basic Server dataclass properties."""
        server_id = utils.generate_uuid()
        nova_server = self.create_nova_server(
            server_id,
            name='my-server',
            status='ACTIVE',
            created='2026-01-01T00:00:00Z',
            tenant_id='tenant-123',
            locked=True,
            metadata={'key': 'value'},
            pinned_availability_zone='az1'
        )

        wrapped = nova_helper.Server.from_novaclient(nova_server)

        self.assertEqual(server_id, wrapped.uuid)
        self.assertEqual('my-server', wrapped.name)
        self.assertEqual('ACTIVE', wrapped.status)
        self.assertEqual('2026-01-01T00:00:00Z', wrapped.created)
        self.assertEqual('tenant-123', wrapped.tenant_id)
        self.assertTrue(wrapped.locked)
        self.assertEqual({'key': 'value'}, wrapped.metadata)
        self.assertEqual('az1', wrapped.pinned_availability_zone)

    def test_server_extended_attributes(self):
        """Test Server dataclass extended attributes."""
        server_id = utils.generate_uuid()
        nova_server = self.create_nova_server(
            server_id,
            **{
                'OS-EXT-SRV-ATTR:host': 'compute-1',
                'OS-EXT-STS:vm_state': 'active',
                'OS-EXT-STS:task_state': None,
                'OS-EXT-STS:power_state': 1,
                'OS-EXT-AZ:availability_zone': 'nova',
            }
        )

        wrapped = nova_helper.Server.from_novaclient(nova_server)

        self.assertEqual('compute-1', wrapped.host)
        self.assertEqual('active', wrapped.vm_state)
        self.assertIsNone(wrapped.task_state)
        self.assertEqual(1, wrapped.power_state)
        self.assertEqual('nova', wrapped.availability_zone)

    def test_server_flavor(self):
        """Test Server dataclass flavor property."""
        server_id = utils.generate_uuid()

        nova_server = self.create_nova_server(
            server_id,
            flavor={'id': 'flavor-123', 'name': 'm1.small'}
        )
        wrapped = nova_helper.Server.from_novaclient(nova_server)
        self.assertEqual({'id': 'flavor-123', 'name': 'm1.small'},
                         wrapped.flavor)

    def test_server_equality(self):
        """Test Server dataclass equality comparison."""
        server_id1 = utils.generate_uuid()
        server_id2 = utils.generate_uuid()

        server1a = nova_helper.Server.from_novaclient(
            self.create_nova_server(server_id1)
        )
        server1b = nova_helper.Server.from_novaclient(
            self.create_nova_server(server_id1)
        )
        server2 = nova_helper.Server.from_novaclient(
            self.create_nova_server(server_id2)
        )

        # Same ID and attributes should be equal
        self.assertEqual(server1a, server1b)

        # Different ID should not be equal
        self.assertNotEqual(server1a, server2)

        # Compare with non-Server object
        self.assertNotEqual(server1a, "not-a-server")
        self.assertIsNotNone(server1a)


class TestHypervisorWrapper(base.TestCase):
    """Test suite for the Hypervisor dataclass."""

    @staticmethod
    def create_nova_hypervisor(hypervisor_id, hostname, **kwargs):
        """Create a real novaclient Hypervisor object.

        :param hypervisor_id: hypervisor UUID
        :param hostname: hypervisor hostname
        :param kwargs: additional hypervisor attributes
        :returns: novaclient.v2.hypervisors.Hypervisor object
        """
        hypervisor_info = {
            'id': hypervisor_id,
            'hypervisor_hostname': hostname,
            'hypervisor_type': kwargs.pop('hypervisor_type', 'QEMU'),
            'state': kwargs.pop('state', 'up'),
            'status': kwargs.pop('status', 'enabled'),
            'vcpus': kwargs.pop('vcpus', 16),
            'vcpus_used': kwargs.pop('vcpus_used', 4),
            'memory_mb': kwargs.pop('memory_mb', 32768),
            'memory_mb_used': kwargs.pop('memory_mb_used', 8192),
            'local_gb': kwargs.pop('local_gb', 500),
            'local_gb_used': kwargs.pop('local_gb_used', 100),
            'service': kwargs.pop('service', {'host': hostname, 'id': 1}),
            'servers': kwargs.pop('servers', None),
        }
        hypervisor_info.update(kwargs)
        return hypervisors.Hypervisor(
            hypervisors.HypervisorManager, info=hypervisor_info)

    def test_hypervisor_basic_properties(self):
        """Test basic Hypervisor dataclass properties."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id,
            hostname,
            hypervisor_type='QEMU',
            state='up',
            status='enabled',
            vcpus=32,
            vcpus_used=8,
            memory_mb=65536,
            memory_mb_used=16384,
            local_gb=1000,
            local_gb_used=250
        )

        wrapped = nova_helper.Hypervisor.from_novaclient(nova_hypervisor)

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

    def test_hypervisor_service_properties(self):
        """Test Hypervisor dataclass service properties."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id,
            hostname,
            service={
                'host': hostname,
                'id': 42,
                'disabled_reason': 'maintenance'
            }
        )

        wrapped = nova_helper.Hypervisor.from_novaclient(nova_hypervisor)

        self.assertEqual(hostname, wrapped.service_host)
        self.assertEqual(42, wrapped.service_id)
        self.assertEqual('maintenance', wrapped.service_disabled_reason)

    def test_hypervisor_service_not_dict(self):
        """Test Hypervisor dataclass when service is not a dict."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id,
            hostname,
            service='not-a-dict'
        )

        wrapped = nova_helper.Hypervisor.from_novaclient(nova_hypervisor)

        self.assertIsNone(wrapped.service_host)
        self.assertIsNone(wrapped.service_id)
        self.assertIsNone(wrapped.service_disabled_reason)

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

        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id,
            hostname,
            servers=[server1, server2]
        )

        wrapped = nova_helper.Hypervisor.from_novaclient(nova_hypervisor)

        # Servers should be wrapped as Server dataclasses
        result_servers = wrapped.servers
        self.assertEqual(2, len(result_servers))
        self.assertEqual(server1_id, result_servers[0]['uuid'])
        self.assertEqual(server2_id, result_servers[1]['uuid'])

    def test_hypervisor_servers_none(self):
        """Test Hypervisor dataclass when servers is None."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id,
            hostname,
            servers=None
        )

        wrapped = nova_helper.Hypervisor.from_novaclient(nova_hypervisor)
        self.assertIsNone(wrapped.servers)

    def test_hypervisor_equality(self):
        """Test Hypervisor dataclass equality comparison."""
        hypervisor_id1 = utils.generate_uuid()
        hypervisor_id2 = utils.generate_uuid()

        hyp1a = nova_helper.Hypervisor.from_novaclient(
            self.create_nova_hypervisor(
                hypervisor_id=hypervisor_id1, hostname='host1'
            )
        )
        hyp1b = nova_helper.Hypervisor.from_novaclient(
            self.create_nova_hypervisor(
                hypervisor_id=hypervisor_id1, hostname='host1'
            )
        )
        hyp2 = nova_helper.Hypervisor.from_novaclient(
            self.create_nova_hypervisor(
                hypervisor_id=hypervisor_id2, hostname='host2'
            )
        )

        # Same ID and attributes should be equal
        self.assertEqual(hyp1a, hyp1b)

        # Different ID should not be equal
        self.assertNotEqual(hyp1a, hyp2)

        # Compare with non-Hypervisor object
        self.assertNotEqual(hyp1a, "not-a-hypervisor")


class TestFlavorWrapper(base.TestCase):
    """Test suite for the Flavor dataclass."""

    @staticmethod
    def create_nova_flavor(flavor_id, name, **kwargs):
        """Create a real novaclient Flavor object.

        :param flavor_id: flavor ID
        :param name: flavor name
        :param kwargs: additional flavor attributes
        :returns: novaclient.v2.flavors.Flavor object
        """
        flavor_info = {
            'id': flavor_id,
            'name': name,
            'vcpus': kwargs.pop('vcpus', 2),
            'ram': kwargs.pop('ram', 2048),
            'disk': kwargs.pop('disk', 20),
            'OS-FLV-EXT-DATA:ephemeral': kwargs.pop('ephemeral', 0),
            'swap': kwargs.pop('swap', ''),
            'os-flavor-access:is_public': kwargs.pop('is_public', True),
        }
        flavor_info.update(kwargs)
        return flavors.Flavor(flavors.FlavorManager, info=flavor_info)

    def test_flavor_basic_properties(self):
        """Test basic Flavor dataclass properties."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            flavor_id,
            'm1.small',
            vcpus=2,
            ram=2048,
            disk=20,
            ephemeral=10,
            swap=512,
            is_public=True
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)

        self.assertEqual(flavor_id, wrapped.id)
        self.assertEqual('m1.small', wrapped.flavor_name)
        self.assertEqual(2, wrapped.vcpus)
        self.assertEqual(2048, wrapped.ram)
        self.assertEqual(20, wrapped.disk)
        self.assertEqual(10, wrapped.ephemeral)
        self.assertEqual(512, wrapped.swap)
        self.assertTrue(wrapped.is_public)

    def test_flavor_empty_swap(self):
        """Test Flavor dataclass with empty swap string."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            flavor_id,
            'm1.noswap',
            swap=''
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)
        self.assertEqual(0, wrapped.swap)

    def test_flavor_private(self):
        """Test Flavor dataclass with private flavor."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            flavor_id,
            'm1.private',
            is_public=False
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)
        self.assertFalse(wrapped.is_public)

    def test_flavor_with_extra_specs(self):
        """Test Flavor dataclass with extra_specs."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            flavor_id,
            'm1.compute',
            extra_specs={'hw:cpu_policy': 'dedicated', 'hw:numa_nodes': '2'}
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)

        self.assertEqual(
            {'hw:cpu_policy': 'dedicated', 'hw:numa_nodes': '2'},
            wrapped.extra_specs
        )

    def test_flavor_without_extra_specs(self):
        """Test Flavor dataclass without extra_specs."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            flavor_id,
            'm1.basic'
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)
        self.assertEqual({}, wrapped.extra_specs)

    def test_flavor_equality(self):
        """Test Flavor dataclass equality comparison."""
        flavor_id1 = utils.generate_uuid()
        flavor_id2 = utils.generate_uuid()

        flavor1a = nova_helper.Flavor.from_novaclient(
            self.create_nova_flavor(flavor_id1, 'm1.small'))
        flavor1b = nova_helper.Flavor.from_novaclient(
            self.create_nova_flavor(flavor_id1, 'm1.small'))
        flavor2 = nova_helper.Flavor.from_novaclient(
            self.create_nova_flavor(flavor_id2, 'm1.large'))

        # Same ID and attributes should be equal
        self.assertEqual(flavor1a, flavor1b)

        # Different ID should not be equal
        self.assertNotEqual(flavor1a, flavor2)

        # Compare with non-Flavor object
        self.assertNotEqual(flavor1a, "not-a-flavor")


class TestAggregateWrapper(base.TestCase):
    """Test suite for the Aggregate dataclass."""

    @staticmethod
    def create_nova_aggregate(aggregate_id, name, **kwargs):
        """Create a real novaclient Aggregate object.

        :param aggregate_id: aggregate ID
        :param name: aggregate name
        :param kwargs: additional aggregate attributes
        :returns: novaclient.v2.aggregates.Aggregate object
        """
        from novaclient.v2 import aggregates

        aggregate_info = {
            'id': aggregate_id,
            'name': name,
            'availability_zone': kwargs.pop('availability_zone', None),
            'hosts': kwargs.pop('hosts', []),
            'metadata': kwargs.pop('metadata', {}),
        }
        aggregate_info.update(kwargs)
        return aggregates.Aggregate(
            aggregates.AggregateManager, info=aggregate_info)

    def test_aggregate_basic_properties(self):
        """Test basic Aggregate dataclass properties."""
        aggregate_id = utils.generate_uuid()
        nova_aggregate = self.create_nova_aggregate(
            aggregate_id,
            'test-aggregate',
            availability_zone='az1',
            hosts=['host1', 'host2', 'host3'],
            metadata={'ssd': 'true', 'gpu': 'nvidia'}
        )

        wrapped = nova_helper.Aggregate.from_novaclient(nova_aggregate)

        self.assertEqual(aggregate_id, wrapped.id)
        self.assertEqual('test-aggregate', wrapped.name)
        self.assertEqual('az1', wrapped.availability_zone)
        self.assertEqual(['host1', 'host2', 'host3'], wrapped.hosts)
        self.assertEqual({'ssd': 'true', 'gpu': 'nvidia'}, wrapped.metadata)

    def test_aggregate_no_az(self):
        """Test Aggregate dataclass without availability zone."""
        aggregate_id = utils.generate_uuid()
        nova_aggregate = self.create_nova_aggregate(
            aggregate_id,
            'test-aggregate',
            availability_zone=None
        )

        wrapped = nova_helper.Aggregate.from_novaclient(nova_aggregate)
        self.assertIsNone(wrapped.availability_zone)

    def test_aggregate_equality(self):
        """Test Aggregate dataclass equality comparison."""
        aggregate_id1 = utils.generate_uuid()
        aggregate_id2 = utils.generate_uuid()

        agg1a = nova_helper.Aggregate.from_novaclient(
            self.create_nova_aggregate(aggregate_id1, 'agg1'))
        agg1b = nova_helper.Aggregate.from_novaclient(
            self.create_nova_aggregate(aggregate_id1, 'agg1'))
        agg2 = nova_helper.Aggregate.from_novaclient(
            self.create_nova_aggregate(aggregate_id2, 'agg2'))

        # Same ID and attributes should be equal
        self.assertEqual(agg1a, agg1b)

        # Different ID should not be equal
        self.assertNotEqual(agg1a, agg2)

        # Compare with non-Aggregate object
        self.assertNotEqual(agg1a, "not-an-aggregate")


class TestServiceWrapper(base.TestCase):
    """Test suite for the Service dataclass."""

    @staticmethod
    def create_nova_service(service_id, **kwargs):
        """Create a real novaclient Service object.

        :param service_id: service ID
        :param kwargs: additional service attributes
        :returns: novaclient.v2.services.Service object
        """
        from novaclient.v2 import services

        service_info = {
            'id': service_id,
            'binary': kwargs.pop('binary', 'nova-compute'),
            'host': kwargs.pop('host', 'compute-1'),
            'zone': kwargs.pop('zone', 'nova'),
            'status': kwargs.pop('status', 'enabled'),
            'state': kwargs.pop('state', 'up'),
            'updated_at': kwargs.pop('updated_at', '2026-01-09T12:00:00Z'),
            'disabled_reason': kwargs.pop('disabled_reason', None),
        }
        service_info.update(kwargs)
        return services.Service(services.ServiceManager, info=service_info)

    def test_service_basic_properties(self):
        """Test basic Service dataclass properties."""
        service_id = utils.generate_uuid()
        nova_service = self.create_nova_service(
            service_id,
            binary='nova-compute',
            host='compute-node-1',
            zone='az1',
            status='enabled',
            state='up',
            updated_at='2026-01-09T12:00:00Z',
            disabled_reason=None
        )

        wrapped = nova_helper.Service.from_novaclient(nova_service)

        self.assertEqual(service_id, wrapped.uuid)
        self.assertEqual('nova-compute', wrapped.binary)
        self.assertEqual('compute-node-1', wrapped.host)
        self.assertEqual('az1', wrapped.zone)
        self.assertEqual('enabled', wrapped.status)
        self.assertEqual('up', wrapped.state)
        self.assertEqual('2026-01-09T12:00:00Z', wrapped.updated_at)
        self.assertIsNone(wrapped.disabled_reason)

    def test_service_disabled(self):
        """Test Service dataclass with disabled service."""
        service_id = utils.generate_uuid()
        nova_service = self.create_nova_service(
            service_id,
            status='disabled',
            state='down',
            disabled_reason='maintenance'
        )

        wrapped = nova_helper.Service.from_novaclient(nova_service)

        self.assertEqual('disabled', wrapped.status)
        self.assertEqual('down', wrapped.state)
        self.assertEqual('maintenance', wrapped.disabled_reason)

    def test_service_equality(self):
        """Test Service dataclass equality comparison."""
        service_id1 = utils.generate_uuid()
        service_id2 = utils.generate_uuid()

        svc1a = nova_helper.Service.from_novaclient(
            self.create_nova_service(service_id1))
        svc1b = nova_helper.Service.from_novaclient(
            self.create_nova_service(service_id1))
        svc2 = nova_helper.Service.from_novaclient(
            self.create_nova_service(service_id2))

        # Same ID and attributes should be equal
        self.assertEqual(svc1a, svc1b)

        # Different ID should not be equal
        self.assertNotEqual(svc1a, svc2)

        # Compare with non-Service object
        self.assertNotEqual(svc1a, "not-a-service")


class TestServerMigrationWrapper(base.TestCase):
    """Test suite for the ServerMigration dataclass."""

    @staticmethod
    def create_nova_migration(migration_id, **kwargs):
        """Create a real novaclient ServerMigration object.

        :param migration_id: migration ID
        :param kwargs: additional migration attributes
        :returns: novaclient.v2.server_migrations.ServerMigration object
        """
        from novaclient.v2 import server_migrations

        migration_info = {
            'id': migration_id,
        }
        migration_info.update(kwargs)
        return server_migrations.ServerMigration(
            server_migrations.ServerMigrationsManager, info=migration_info)

    def test_migration_basic_properties(self):
        """Test basic ServerMigration dataclass properties."""
        migration_id = utils.generate_uuid()
        nova_migration = self.create_nova_migration(migration_id)

        wrapped = nova_helper.ServerMigration.from_novaclient(nova_migration)
        self.assertEqual(migration_id, wrapped.id)

    def test_migration_equality(self):
        """Test ServerMigration dataclass equality comparison."""
        migration_id1 = utils.generate_uuid()
        migration_id2 = utils.generate_uuid()

        mig1a = nova_helper.ServerMigration.from_novaclient(
            self.create_nova_migration(migration_id1))
        mig1b = nova_helper.ServerMigration.from_novaclient(
            self.create_nova_migration(migration_id1))
        mig2 = nova_helper.ServerMigration.from_novaclient(
            self.create_nova_migration(migration_id2))

        # Same ID and attributes should be equal
        self.assertEqual(mig1a, mig1b)

        # Different ID should not be equal
        self.assertNotEqual(mig1a, mig2)

        # Compare with non-ServerMigration object
        self.assertNotEqual(mig1a, "not-a-migration")
