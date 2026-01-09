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
from novaclient.v2 import servers

from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import utils
from watcher import conf
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils

CONF = conf.CONF


@mock.patch.object(clients.OpenStackClients, 'nova')
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
            nova_util.nova.server_migrations.list.return_value = []
        else:
            nova_util.nova.server_migration.list.return_value = [fake_list]

    def test_get_compute_node_by_hostname(
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        hypervisor_id = utils.generate_uuid()
        hypervisor_name = "fake_hypervisor_1"
        hypervisor = self.create_nova_hypervisor(
            hypervisor_id=hypervisor_id,
            hostname=hypervisor_name
        )
        nova_util.nova.hypervisors.search.return_value = [hypervisor]
        # verify that the compute node can be obtained normally by name
        compute_node = nova_util.get_compute_node_by_hostname(hypervisor_name)
        self.assertEqual(
            compute_node, nova_helper.Hypervisor.from_novaclient(hypervisor))

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
            node = self.create_nova_hypervisor(
                hypervisor_id=utils.generate_uuid(),
                hostname=hostname,
                service={'host': hostname}
            )
            nodes.append(node)
        # We should get back exact matches based on the service host.
        nova_util.nova.hypervisors.search.return_value = nodes
        for index, name in enumerate(['compute1', 'compute10']):
            result = nova_util.get_compute_node_by_hostname(name)
            self.assertEqual(
                nova_helper.Hypervisor.from_novaclient(nodes[index]), result)

    def test_get_compute_node_by_uuid(
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        hypervisor_id = utils.generate_uuid()
        hypervisor_name = "fake_hypervisor_1"
        hypervisor = self.create_nova_hypervisor(
            hypervisor_id=hypervisor_id,
            hostname=hypervisor_name
        )
        nova_util.nova.hypervisors.get.return_value = hypervisor
        # verify that the compute node can be obtained normally by id
        compute_node = nova_util.get_compute_node_by_uuid(hypervisor_id)
        self.assertEqual(
            compute_node, nova_helper.Hypervisor.from_novaclient(hypervisor))

    def test_get_instance_list(self, *args):
        nova_util = nova_helper.NovaHelper()
        # Call it once with no filters.
        with mock.patch.object(nova_util, 'nova') as nova_mock:
            result = nova_util.get_instance_list()
            nova_mock.servers.list.assert_called_once_with(
                search_opts={'all_tenants': True}, marker=None, limit=-1)
            self.assertEqual([], result)
        # Call it again with filters.
        with mock.patch.object(nova_util, 'nova') as nova_mock:
            result = nova_util.get_instance_list(filters={'host': 'fake-host'})
            nova_mock.servers.list.assert_called_once_with(
                search_opts={'all_tenants': True, 'host': 'fake-host'},
                marker=None, limit=-1)
            self.assertEqual([], result)

    def test_stop_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        # verify that the method will return True when stopped
        kwargs = {
            "id": instance_id,
            "OS-EXT-STS:vm_state": "stopped"
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        result = nova_util.stop_instance(instance_id)
        self.assertTrue(result)

        # verify that the method will return False when active
        kwargs = {
            "id": instance_id,
            "OS-EXT-STS:vm_state": "active"
        }
        server = self.create_nova_server(**kwargs)
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
        nova_util.nova.servers.get.side_effect = nvexceptions.NotFound("404")
        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

    def test_start_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        # verify that the method will return True when active
        kwargs = {
            "id": instance_id,
            "OS-EXT-STS:vm_state": "active"
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        result = nova_util.start_instance(instance_id)
        self.assertTrue(result)

        # verify that the method will return False when stopped
        kwargs = {
            "id": instance_id,
            "OS-EXT-STS:vm_state": "stopped"
        }
        server = self.create_nova_server(**kwargs)
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
        nova_util.nova.servers.get.side_effect = nvexceptions.NotFound("404")
        result = nova_util.start_instance(instance_id)
        self.assertFalse(result)

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_resize', autospec=True
    )
    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_confirm_resize', autospec=True
    )
    def test_resize_instance(self, mock_confirm_resize, mock_resize,
                             mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "VERIFY_RESIZE",
            "OS-EXT-STS:vm_state": "resized"
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        flavor = self.create_nova_flavor(
            id=self.flavor_name, name=self.flavor_name
        )
        nova_util.nova.flavors.get.return_value = flavor
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
    def test_resize_instance_wrong_status(self, mock_resize,
                                          mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "SOMETHING_ELSE",
            "OS-EXT-STS:vm_state": "resizing"
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        flavor = self.create_nova_flavor(
            id=self.flavor_name, name=self.flavor_name
        )
        nova_util.nova.flavors.get.return_value = flavor
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertFalse(is_success)
        mock_resize.assert_called_once_with(
            nova_util, self.instance_uuid, self.flavor_name
        )

    @mock.patch.object(servers.Server, 'confirm_resize', autospec=True)
    @mock.patch.object(servers.Server, 'resize', autospec=True)
    def test_watcher_resize_instance_retry_success(
            self, mock_resize, mock_confirm_resize, mock_cinder, mock_nova):
        """Test that resize_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": "RESIZING",
            "OS-EXT-STS:vm_state": "resizing"
        }
        server = self.create_nova_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "status": "VERIFY_RESIZE",
            "OS-EXT-STS:vm_state": "resized"
        }
        resized_server = self.create_nova_server(**kwargs)

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
        kwargs = {
            "id": self.instance_uuid,
            "status": "RESIZING",
            "OS-EXT-STS:vm_state": "resizing"
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server)

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
            "id": self.instance_uuid,
            "status": "RESIZING",
            "OS-EXT-STS:vm_state": "resizing"
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server)

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
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.destination_node
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

        # verify that the method will return False when the instance does
        # not exist.
        nova_util.nova.servers.get.side_effect = nvexceptions.NotFound("404")
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

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_live_migrate', autospec=True
    )
    def test_live_migrate_instance_with_task_state(
            self, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": ""
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.mock_sleep.assert_not_called()

        kwargs["OS-EXT-STS:task_state"] = 'migrating'
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)
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
            self, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_nova_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.destination_node,
            "status": "ACTIVE"
        }
        migrated_server = self.create_nova_server(**kwargs)

        nova_util.nova.servers.get.side_effect = (
            server, server, migrated_server)

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
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_util.nova.servers.get.side_effect = nvexceptions.NotFound("404")

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node)

        self.assertFalse(is_success)

    def test_abort_live_migrate_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": None
        }
        server = self.create_nova_server(**kwargs)
        migration = self.create_nova_migration(2)
        self.fake_nova_migration_list(nova_util, fake_list=migration)

        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        self.assertTrue(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.destination_node,
            "OS-EXT-STS:task_state": None
        }
        server = self.create_nova_server(**kwargs)

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
            "id": self.instance_uuid,
            "OS-EXT-STS:task_state": "fake_task_state",
            "OS-EXT-SRV-ATTR:host": self.destination_node
        }
        server = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        self.fake_nova_migration_list(nova_util, fake_list=None)
        self.assertFalse(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_migrate', autospec=True
    )
    @mock.patch.object(nova_helper.NovaHelper, 'confirm_resize', autospec=True)
    def test_non_live_migrate_instance_no_destination_node(
            self, mock_confirm_resize, mock_migrate, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_nova_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.destination_node,
            "status": "VERIFY_RESIZE"
        }
        migrated_server = self.create_nova_server(**kwargs)

        nova_util.nova.servers.get.side_effect = (
            server, server, server, migrated_server)

        self.destination_node = None
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)
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
            self, mock_migrate, mock_confirm_resize, mock_cinder, mock_nova):
        """Test that watcher_non_live_migrate uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "status": 'MIGRATING',  # Never reaches ACTIVE
            "OS-EXT-SRV-ATTR:host": self.source_node
        }
        server = self.create_nova_server(**kwargs)

        kwargs = {
            "id": self.instance_uuid,
            "status": 'VERIFY_RESIZE',
            "OS-EXT-SRV-ATTR:host": self.destination_node
        }
        verify_server = self.create_nova_server(**kwargs)

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
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that watcher_non_live_migrate uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_nova_server(**kwargs)

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

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
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that watcher_non_live_migrate respects explicit retry value"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node
        }
        server = self.create_nova_server(**kwargs)
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
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.create_nova_server(**kwargs)

        kwargs["OS-EXT-SRV-ATTR:host"] = self.destination_node
        migrated_server = self.create_nova_server(**kwargs)

        nova_util.nova.servers.get.side_effect = (
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
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.create_nova_server(**kwargs)

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

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
            self, mock_migrate, mock_cinder, mock_nova):
        """Test that live_migrate_instance uses config timeout by default"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "OS-EXT-STS:task_state": "migrating"
        }
        server = self.create_nova_server(**kwargs)

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
            self, mock_migrate, mock_cinder, mock_nova):
        """Test live_migrate with no destination uses config timeout"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_nova_server(**kwargs)

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

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
            self, mock_migrate, mock_cinder, mock_nova):
        """Test live_migrate with no destination uses config timeout"""
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid,
            "OS-EXT-SRV-ATTR:host": self.source_node,
            "status": "MIGRATING"
        }
        server = self.create_nova_server(**kwargs)

        # Set config value
        self.flags(migration_max_retries=10, migration_interval=3,
                   group='nova')

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

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

    @mock.patch.object(
        nova_helper.NovaHelper, '_instance_confirm_resize', autospec=True
    )
    def test_confirm_resize(self, mock_confirm_resize, mock_cinder,
                            mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=instance,
                                 fake_list=None)

        server = nova_helper.Server.from_novaclient(instance)
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

    def test_get_compute_node_list(
            self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        hypervisor1_id = utils.generate_uuid()
        hypervisor1_name = "fake_hypervisor_1"
        hypervisor1 = self.create_nova_hypervisor(
            hypervisor_id=hypervisor1_id, hostname=hypervisor1_name,
            hypervisor_type="QEMU"
        )

        hypervisor2_id = utils.generate_uuid()
        hypervisor2_name = "fake_ironic"
        hypervisor2 = self.create_nova_hypervisor(
            hypervisor_id=hypervisor2_id, hostname=hypervisor2_name,
            hypervisor_type="ironic"
        )

        nova_util.nova.hypervisors.list.return_value = [hypervisor1,
                                                        hypervisor2]

        compute_nodes = nova_util.get_compute_node_list()

        # baremetal node should be removed
        self.assertEqual(1, len(compute_nodes))
        self.assertEqual(hypervisor1_name,
                         compute_nodes[0].hypervisor_hostname)

    def test_find_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=instance, fake_list=None)

        result = nova_util.find_instance(self.instance_uuid)
        self.assertEqual(1, nova_util.nova.servers.get.call_count)
        self.mock_sleep.assert_not_called()
        self.assertEqual(nova_helper.Server.from_novaclient(instance), result)

    def test_find_instance_retries(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        self.fake_nova_find_list(nova_util, fake_find=instance,
                                 fake_list=None)
        nova_util.nova.servers.get.side_effect = [
            ksa_exc.ConnectionError("Connection failed"),
            instance
        ]

        result = nova_util.find_instance(self.instance_uuid)
        self.assertEqual(2, nova_util.nova.servers.get.call_count)
        self.assertEqual(1, self.mock_sleep.call_count)
        self.assertEqual(nova_helper.Server.from_novaclient(instance), result)

    def test_find_instance_retries_exhausts_retries(self, mock_cinder,
                                                    mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
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
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        nova_util._nova_start_instance(instance.id)
        nova_util.nova.servers.start.assert_called_once_with(instance.id)

    def test_nova_stop_instance(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        nova_util._nova_stop_instance(instance.id)
        nova_util.nova.servers.stop.assert_called_once_with(instance.id)

    def test_instance_resize(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        flavor_name = "m1.small"

        result = nova_util._instance_resize(instance, flavor_name)
        nova_util.nova.servers.resize.assert_called_once_with(
            instance, flavor=flavor_name
        )
        self.assertTrue(result)

    def test_instance_confirm_resize(self, mock_cinder,
                                     mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        nova_util._instance_confirm_resize(instance)
        nova_util.nova.servers.confirm_resize.assert_called_once_with(instance)

    def test_instance_live_migrate(self, mock_cinder,
                                   mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        dest_hostname = "dest_hostname"
        nova_util._instance_live_migrate(instance, dest_hostname)
        nova_util.nova.servers.live_migrate.assert_called_once_with(
            instance, "dest_hostname", block_migration='auto'
        )

    def test_instance_migrate(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        dest_hostname = "dest_hostname"
        nova_util._instance_migrate(instance, dest_hostname)
        nova_util.nova.servers.migrate.assert_called_once_with(
            instance, host="dest_hostname"
        )

    def test_live_migration_abort(self, mock_cinder, mock_nova):
        nova_util = nova_helper.NovaHelper()
        kwargs = {
            "id": self.instance_uuid
        }
        instance = self.create_nova_server(**kwargs)
        nova_util._live_migration_abort(instance.id, 1)
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

    def test_server_basic_properties(self):
        """Test basic Server dataclass properties."""
        server_id = utils.generate_uuid()
        nova_server = self.create_nova_server(
            id=server_id,
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
            id=server_id,
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
            id=server_id,
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
            self.create_nova_server(id=server_id1)
        )
        server1b = nova_helper.Server.from_novaclient(
            self.create_nova_server(id=server_id1)
        )
        server2 = nova_helper.Server.from_novaclient(
            self.create_nova_server(id=server_id2)
        )

        # Same ID and attributes should be equal
        self.assertEqual(server1a, server1b)

        # Different ID should not be equal
        self.assertNotEqual(server1a, server2)

        # Compare with non-Server object
        self.assertNotEqual(server1a, "not-a-server")
        self.assertIsNotNone(server1a)


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

    def test_hypervisor_basic_properties(self):
        """Test basic Hypervisor dataclass properties."""
        hypervisor_id = utils.generate_uuid()
        hostname = 'compute-node-1'
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id=hypervisor_id,
            hostname=hostname,
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
        hostname = 'compute-node-1'
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id=utils.generate_uuid(),
            hostname=hostname,
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
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id=utils.generate_uuid(),
            hostname='compute-node-1',
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
            hypervisor_id=hypervisor_id,
            hostname=hostname,
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
        nova_hypervisor = self.create_nova_hypervisor(
            hypervisor_id=utils.generate_uuid(),
            hostname='compute-node-1',
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


class TestFlavorWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the Flavor dataclass."""

    def test_flavor_basic_properties(self):
        """Test basic Flavor dataclass properties."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            id=flavor_id,
            name='m1.small',
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
            id=flavor_id,
            name='m1.noswap',
            swap=''
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)
        self.assertEqual(0, wrapped.swap)

    def test_flavor_private(self):
        """Test Flavor dataclass with private flavor."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            id=flavor_id,
            name='m1.private',
            is_public=False
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)
        self.assertFalse(wrapped.is_public)

    def test_flavor_with_extra_specs(self):
        """Test Flavor dataclass with extra_specs."""
        flavor_id = utils.generate_uuid()
        nova_flavor = self.create_nova_flavor(
            id=flavor_id,
            name='m1.compute',
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
            id=flavor_id,
            name='m1.basic'
        )

        wrapped = nova_helper.Flavor.from_novaclient(nova_flavor)
        self.assertEqual({}, wrapped.extra_specs)

    def test_flavor_equality(self):
        """Test Flavor dataclass equality comparison."""
        flavor_id1 = utils.generate_uuid()
        flavor_id2 = utils.generate_uuid()

        flavor1a = nova_helper.Flavor.from_novaclient(
            self.create_nova_flavor(id=flavor_id1, name='m1.small'))
        flavor1b = nova_helper.Flavor.from_novaclient(
            self.create_nova_flavor(id=flavor_id1, name='m1.small'))
        flavor2 = nova_helper.Flavor.from_novaclient(
            self.create_nova_flavor(id=flavor_id2, name='m1.large'))

        # Same ID and attributes should be equal
        self.assertEqual(flavor1a, flavor1b)

        # Different ID should not be equal
        self.assertNotEqual(flavor1a, flavor2)

        # Compare with non-Flavor object
        self.assertNotEqual(flavor1a, "not-a-flavor")


class TestAggregateWrapper(test_utils.NovaResourcesMixin, base.TestCase):
    """Test suite for the Aggregate dataclass."""

    def test_aggregate_basic_properties(self):
        """Test basic Aggregate dataclass properties."""
        aggregate_id = utils.generate_uuid()
        nova_aggregate = self.create_nova_aggregate(
            id=aggregate_id,
            name='test-aggregate',
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
            id=aggregate_id,
            name='test-aggregate',
            availability_zone=None
        )

        wrapped = nova_helper.Aggregate.from_novaclient(nova_aggregate)
        self.assertIsNone(wrapped.availability_zone)

    def test_aggregate_equality(self):
        """Test Aggregate dataclass equality comparison."""
        aggregate_id1 = utils.generate_uuid()
        aggregate_id2 = utils.generate_uuid()

        agg1a = nova_helper.Aggregate.from_novaclient(
            self.create_nova_aggregate(id=aggregate_id1, name='agg1'))
        agg1b = nova_helper.Aggregate.from_novaclient(
            self.create_nova_aggregate(id=aggregate_id1, name='agg1'))
        agg2 = nova_helper.Aggregate.from_novaclient(
            self.create_nova_aggregate(id=aggregate_id2, name='agg2'))

        # Same ID and attributes should be equal
        self.assertEqual(agg1a, agg1b)

        # Different ID should not be equal
        self.assertNotEqual(agg1a, agg2)

        # Compare with non-Aggregate object
        self.assertNotEqual(agg1a, "not-an-aggregate")


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

    def test_service_basic_properties(self):
        """Test basic Service dataclass properties."""
        service_id = utils.generate_uuid()
        nova_service = self.create_nova_service(
            id=service_id,
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
            id=service_id,
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
            self.create_nova_service(id=service_id1))
        svc1b = nova_helper.Service.from_novaclient(
            self.create_nova_service(id=service_id1))
        svc2 = nova_helper.Service.from_novaclient(
            self.create_nova_service(id=service_id2))

        # Same ID and attributes should be equal
        self.assertEqual(svc1a, svc1b)

        # Different ID should not be equal
        self.assertNotEqual(svc1a, svc2)

        # Compare with non-Service object
        self.assertNotEqual(svc1a, "not-a-service")


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
            raise nvexceptions.NotFound("404")

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
            raise nvexceptions.NotFound("404")

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
            raise nvexceptions.NotFound("404")

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
            raise nvexceptions.NotFound("404")

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
            raise nvexceptions.NotFound("404")

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
            raise nvexceptions.ClientException("Nova error")

        self.assertRaises(
            exception.NovaClientError, mock_function, None, "instance-123")

    def test_handle_nova_error_logs_client_exception(self):
        """Test that ClientException is logged before re-raising."""
        @nova_helper.handle_nova_error("Instance")
        def mock_function(self, instance_id):
            raise nvexceptions.ClientException("Nova error")

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
