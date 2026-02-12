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

import fixtures
import time
from unittest import mock

from novaclient import api_versions

import glanceclient.exc as glexceptions
import novaclient.exceptions as nvexceptions
from novaclient.v2 import flavors
from novaclient.v2 import hypervisors
from novaclient.v2 import servers

from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import utils
from watcher import conf
from watcher.tests import base

CONF = conf.CONF


@mock.patch.object(clients.OpenStackClients, 'nova')
@mock.patch.object(clients.OpenStackClients, 'neutron')
@mock.patch.object(clients.OpenStackClients, 'cinder')
@mock.patch.object(clients.OpenStackClients, 'glance')
class TestNovaHelper(base.TestCase):

    def setUp(self):
        super(TestNovaHelper, self).setUp()
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
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
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
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
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

    def test_stop_instance(self, mock_glance, mock_cinder, mock_neutron,
                           mock_nova):
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

    def test_start_instance(self, mock_glance, mock_cinder, mock_neutron,
                            mock_nova):
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

    def test_delete_instance(self, mock_glance, mock_cinder, mock_neutron,
                             mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()

        # verify that the method will return False when the instance does
        # not exist.
        self.fake_nova_find_list(nova_util, fake_find=None, fake_list=None)
        result = nova_util.delete_instance(instance_id)
        self.assertFalse(result)

        # verify that the method will return True when the instance exists.
        server = self.fake_server(instance_id)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        result = nova_util.delete_instance(instance_id)
        self.assertTrue(result)

    @mock.patch.object(servers.Server, 'resize', autospec=True)
    @mock.patch.object(servers.Server, 'confirm_resize', autospec=True)
    def test_resize_instance(self, mock_confirm_resize, mock_resize,
                             mock_glance, mock_cinder, mock_neutron,
                             mock_nova):
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
    def test_resize_instance_wrong_status(self, mock_resize, mock_glance,
                                          mock_cinder, mock_neutron,
                                          mock_nova):
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
            self, mock_resize, mock_confirm_resize, mock_glance, mock_cinder,
            mock_neutron, mock_nova):
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
            self, mock_resize, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
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
    def test_live_migrate_instance(self, mock_migrate, mock_glance,
                                   mock_cinder, mock_neutron,
                                   mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        self.fake_nova_find_list(nova_util, fake_find=None, fake_list=None)

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node)

        self.assertFalse(is_success)

    def test_abort_live_migrate_instance(self, mock_glance, mock_cinder,
                                         mock_neutron, mock_nova):
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
            self, mock_confirm_resize, mock_migrate, mock_glance, mock_cinder,
            mock_neutron, mock_nova):
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

    def test_create_image_from_instance(self, mock_glance, mock_cinder,
                                        mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        image = mock.MagicMock()
        setattr(instance, 'OS-EXT-SRV-ATTR:host', self.source_node)
        setattr(instance, 'OS-EXT-STS:vm_state', "stopped")
        self.fake_nova_find_list(
            nova_util,
            fake_find=instance,
            fake_list=instance)
        image_uuid = 'fake-image-uuid'
        nova_util.nova.servers.create_image.return_value = image

        glance_client = mock.MagicMock()
        mock_glance.return_value = glance_client

        glance_client.images = {image_uuid: image}
        instance = nova_util.create_image_from_instance(
            self.instance_uuid, "Cirros"
        )
        self.assertIsNotNone(instance)

        nova_util.glance.images.get.return_value = None
        instance = nova_util.create_image_from_instance(
            self.instance_uuid, "Cirros"
        )
        self.assertIsNone(instance)

    @mock.patch.object(nova_helper.NovaHelper, 'confirm_resize', autospec=True)
    @mock.patch.object(servers.Server, 'migrate', autospec=True)
    def test_watcher_non_live_migrate_instance_retry_success(
            self, mock_migrate, mock_confirm_resize, mock_glance, mock_cinder,
            mock_neutron, mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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
            self, mock_migrate, mock_glance, mock_cinder, mock_neutron,
            mock_nova):
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

    def test_enable_service_nova_compute(self, mock_glance, mock_cinder,
                                         mock_neutron, mock_nova):
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

    def test_disable_service_nova_compute(self, mock_glance, mock_cinder,
                                          mock_neutron, mock_nova):
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

    def test_create_instance(self, mock_glance, mock_cinder, mock_neutron,
                             mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        nova_util.nova.servers.create.return_value = instance
        nova_util.nova.servers.get.return_value = instance

        create_instance = nova_util.create_instance(
            self.source_node, create_new_floating_ip=False)
        self.assertIsNotNone(create_instance)
        self.assertEqual(create_instance, instance)

        # verify that the method create_instance will return None when
        # the method findall raises exception.
        nova_util.nova.keypairs.findall.side_effect = nvexceptions.NotFound(
            404)
        instance = nova_util.create_instance(self.source_node)
        self.assertIsNone(instance)
        nova_util.nova.keypairs.findall.side_effect = None

        # verify that the method create_instance will return None when
        # the method get raises exception.
        nova_util.glance.images.get.side_effect = glexceptions.NotFound(404)
        instance = nova_util.create_instance(self.source_node)
        self.assertIsNone(instance)
        nova_util.glance.images.get.side_effect = None

        # verify that the method create_instance will return None when
        # the method find raises exception.
        nova_util.nova.flavors.find.side_effect = nvexceptions.NotFound(404)
        instance = nova_util.create_instance(self.source_node)
        self.assertIsNone(instance)
        nova_util.nova.flavors.find.side_effect = None

        # verify that the method create_instance will return None when
        # the method get_security_group_id_from_name return None.
        with mock.patch.object(
            nova_util,
            'get_security_group_id_from_name',
            return_value=None
        ) as mock_security_group_id:
            instance = nova_util.create_instance(self.source_node)
            self.assertIsNone(instance)
            mock_security_group_id.assert_called_once_with("default")

        # verify that the method create_instance will return None when
        # the method get_network_id_from_name return None.
        with mock.patch.object(
            nova_util,
            'get_network_id_from_name',
            return_value=None
        ) as mock_get_network_id:
            instance = nova_util.create_instance(self.source_node)
            self.assertIsNone(instance)
            mock_get_network_id.assert_called_once_with("demo-net")

        # verify that the method create_instance will not return None when
        # the method wait_for_instance_status return True.
        with mock.patch.object(
            nova_util,
            'wait_for_instance_status',
            return_value=True
        ) as mock_instance_status:
            instance = nova_util.create_instance(
                self.source_node, create_new_floating_ip=False)
            self.assertIsNotNone(instance)
            mock_instance_status.assert_called_once_with(
                mock.ANY,
                ('ACTIVE', 'ERROR'),
                5,
                10)

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock()
        volume.id = kwargs.get('id', '45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba')
        volume.size = kwargs.get('size', '1')
        volume.status = kwargs.get('status', 'available')
        volume.snapshot_id = kwargs.get('snapshot_id', None)
        volume.availability_zone = kwargs.get('availability_zone', 'nova')
        return volume

    def test_swap_volume(self, mock_glance, mock_cinder,
                         mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)

        old_volume = self.fake_volume(
            status='in-use', attachments=[{'server_id': self.instance_uuid}])
        new_volume = self.fake_volume(
            id=utils.generate_uuid(), status='in-use')

        result = nova_util.swap_volume(old_volume, new_volume)
        self.assertTrue(result)

        # verify that the method will return False when the status of
        # new_volume is 'fake-use'.
        new_volume = self.fake_volume(
            id=utils.generate_uuid(), status='fake-use')
        result = nova_util.swap_volume(old_volume, new_volume)
        self.assertFalse(result)

    def test_wait_for_volume_status(self, mock_glance, mock_cinder,
                                    mock_neutron, mock_nova):
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
    def test_check_nova_api_version(self, mock_glance, mock_cinder,
                                    mock_neutron, mock_nova):
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

    def test_wait_for_instance_status(self, mock_glance, mock_cinder,
                                      mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)

        # verify that the method will return True when the status of instance
        # is in the expected status.
        result = nova_util.wait_for_instance_status(
            instance,
            ('ACTIVE', 'ERROR'),
            5,
            10)
        self.assertTrue(result)

        # verify that the method will return False when the instance is None.
        result = nova_util.wait_for_instance_status(
            None,
            ('ACTIVE', 'ERROR'),
            5,
            10)
        self.assertFalse(result)

        # verify that the method will return False when the status of instance
        # is not in the expected status.
        self.fake_nova_find_list(nova_util, fake_find=instance, fake_list=None)
        result = nova_util.wait_for_instance_status(
            instance,
            ('ERROR'),
            5,
            10)
        self.assertFalse(result)

    @mock.patch.object(servers.Server, 'confirm_resize', autospec=True)
    def test_confirm_resize(self, mock_confirm_resize, mock_glance,
                            mock_cinder, mock_neutron,
                            mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, fake_find=instance, fake_list=None)

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
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
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
