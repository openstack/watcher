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

import time
from unittest import mock

from novaclient import api_versions


import glanceclient.exc as glexceptions
import novaclient.exceptions as nvexceptions

from watcher.common import clients
from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import utils
from watcher.tests import base


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

    @staticmethod
    def fake_server(*args, **kwargs):
        server = mock.MagicMock()
        server.id = args[0]
        server.status = 'ACTIVE'

        return server

    @staticmethod
    def fake_hypervisor(*args, **kwargs):
        hypervisor = mock.MagicMock()
        hypervisor.id = args[0]
        service_dict = {"host": args[1]}
        hypervisor.service = service_dict
        hypervisor.hypervisor_hostname = args[1]
        hypervisor.hypervisor_type = kwargs.pop('hypervisor_type', 'QEMU')

        return hypervisor

    @staticmethod
    def fake_migration(*args, **kwargs):
        migration = mock.MagicMock()
        migration.id = args[0]
        return migration

    @staticmethod
    def fake_nova_find_list(nova_util, fake_find=None, fake_list=None):
        nova_util.nova.servers.get.return_value = fake_find
        if list is None:
            nova_util.nova.servers.list.return_value = []
        else:
            nova_util.nova.servers.list.return_value = [fake_list]

    @staticmethod
    def fake_nova_hypervisor_list(nova_util, fake_find=None, fake_list=None):
        nova_util.nova.hypervisors.get.return_value = fake_find
        nova_util.nova.hypervisors.list.return_value = fake_list

    @staticmethod
    def fake_nova_migration_list(nova_util, fake_list=None):
        if list is None:
            nova_util.nova.server_migrations.list.return_value = None
        else:
            nova_util.nova.server_migration.list.return_value = [fake_list]

    @staticmethod
    def fake_live_migrate(server, *args, **kwargs):

        def side_effect(*args, **kwargs):
            setattr(server, 'OS-EXT-SRV-ATTR:host', "compute-2")

        server.live_migrate.side_effect = side_effect

    @staticmethod
    def fake_confirm_resize(server, *args, **kwargs):

        def side_effect(*args, **kwargs):
            setattr(server, 'status', 'ACTIVE')

        server.confirm_resize.side_effect = side_effect

    @staticmethod
    def fake_cold_migrate(server, *args, **kwargs):

        def side_effect(*args, **kwargs):
            setattr(server, 'OS-EXT-SRV-ATTR:host', "compute-2")
            setattr(server, 'status', 'VERIFY_RESIZE')

        server.migrate.side_effect = side_effect

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

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_stop_instance(self, mock_glance, mock_cinder, mock_neutron,
                           mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance_id = utils.generate_uuid()
        server = self.fake_server(instance_id)
        setattr(server, 'OS-EXT-STS:vm_state', 'stopped')
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        result = nova_util.stop_instance(instance_id)
        self.assertTrue(result)

        setattr(server, 'OS-EXT-STS:vm_state', 'active')
        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)

        result = nova_util.stop_instance(instance_id)
        self.assertFalse(result)

        # verify that the method will return True when the state of instance
        # is in the expected state.
        setattr(server, 'OS-EXT-STS:vm_state', 'active')
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

    @mock.patch.object(time, 'sleep', mock.Mock())
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

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_resize_instance(self, mock_glance, mock_cinder,
                             mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'status', 'VERIFY_RESIZE')
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertTrue(is_success)

        setattr(server, 'status', 'SOMETHING_ELSE')
        is_success = nova_util.resize_instance(self.instance_uuid,
                                               self.flavor_name)
        self.assertFalse(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_live_migrate_instance(self, mock_glance, mock_cinder,
                                   mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.destination_node)
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.source_node)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

        # verify that the method will return False when the instance does
        # not exist.
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.source_node)
        self.fake_nova_find_list(nova_util, fake_find=None, fake_list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertFalse(is_success)

        # verify that the method will return False when the instance status
        # is in other cases.
        setattr(server, 'status', 'fake_status')
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, None
        )
        self.assertFalse(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_live_migrate_instance_with_task_state(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.source_node)
        setattr(server, 'OS-EXT-STS:task_state', '')
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        time.sleep.assert_not_called()

        setattr(server, 'OS-EXT-STS:task_state', 'migrating')
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        time.sleep.assert_called_with(1)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_live_migrate_instance_no_destination_node(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        self.destination_node = None
        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)
        self.fake_live_migrate(server)
        is_success = nova_util.live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

    def test_watcher_non_live_migrate_instance_not_found(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        self.fake_nova_find_list(nova_util, fake_find=None, fake_list=None)

        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid,
            self.destination_node)

        self.assertFalse(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_abort_live_migrate_instance(self, mock_glance, mock_cinder,
                                         mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                        self.source_node)
        setattr(server, 'OS-EXT-STS:task_state', None)
        migration = self.fake_migration(2)
        self.fake_nova_migration_list(nova_util, fake_list=migration)

        self.fake_nova_find_list(
            nova_util,
            fake_find=server,
            fake_list=server)

        self.assertTrue(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        setattr(server, 'OS-EXT-SRV-ATTR:host', self.destination_node)

        self.assertFalse(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

        setattr(server, 'status', 'ERROR')
        self.assertRaises(
            Exception,
            nova_util.abort_live_migrate,
            self.instance_uuid,
            self.source_node,
            self.destination_node)

        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-STS:task_state', "fake_task_state")
        setattr(server, 'OS-EXT-SRV-ATTR:host', self.destination_node)
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=None)
        self.fake_nova_migration_list(nova_util, fake_list=None)
        self.assertFalse(nova_util.abort_live_migrate(
            self.instance_uuid, self.source_node, self.destination_node))

    def test_non_live_migrate_instance_no_destination_node(
            self, mock_glance, mock_cinder, mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        server = self.fake_server(self.instance_uuid)
        setattr(server, 'OS-EXT-SRV-ATTR:host',
                self.source_node)
        self.destination_node = None
        self.fake_nova_find_list(nova_util, fake_find=server, fake_list=server)
        self.fake_cold_migrate(server)
        self.fake_confirm_resize(server)
        is_success = nova_util.watcher_non_live_migrate_instance(
            self.instance_uuid, self.destination_node
        )
        self.assertTrue(is_success)

    @mock.patch.object(time, 'sleep', mock.Mock())
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

    def test_enable_service_nova_compute(self, mock_glance, mock_cinder,
                                         mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_services = nova_util.nova.services
        nova_services.enable.return_value = mock.MagicMock(
            status='enabled')

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertTrue(result)

        nova_services.enable.return_value = mock.MagicMock(
            status='disabled')

        result = nova_util.enable_service_nova_compute('nanjing')
        self.assertFalse(result)

    def test_disable_service_nova_compute(self, mock_glance, mock_cinder,
                                          mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        nova_services = nova_util.nova.services
        nova_services.disable_log_reason.return_value = mock.MagicMock(
            status='enabled')

        result = nova_util.disable_service_nova_compute('nanjing')
        self.assertFalse(result)

        nova_services.disable_log_reason.return_value = mock.MagicMock(
            status='disabled')

        result = nova_util.disable_service_nova_compute('nanjing')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_create_instance(self, mock_glance, mock_cinder,
                             mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        nova_util.nova.servers.create.return_value = instance
        nova_util.nova.servers.get.return_value = instance

        create_instance = nova_util.create_instance(self.source_node)
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
            instance = nova_util.create_instance(self.source_node)
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

    @mock.patch.object(time, 'sleep', mock.Mock())
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

    @mock.patch.object(time, 'sleep', mock.Mock())
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

    def test_check_nova_api_version(self, mock_glance, mock_cinder,
                                    mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()

        # verify that the method will return True when the version of nova_api
        # is supported.
        api_versions.APIVersion = mock.MagicMock()
        result = nova_util._check_nova_api_version(nova_util.nova, "2.56")
        self.assertTrue(result)

        # verify that the method will return False when the version of nova_api
        # is not supported.
        side_effect = nvexceptions.UnsupportedVersion()
        api_versions.discover_version = mock.MagicMock(
            side_effect=side_effect)
        result = nova_util._check_nova_api_version(nova_util.nova, "2.56")
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
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

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_confirm_resize(self, mock_glance, mock_cinder,
                            mock_neutron, mock_nova):
        nova_util = nova_helper.NovaHelper()
        instance = self.fake_server(self.instance_uuid)
        self.fake_nova_find_list(nova_util, fake_find=instance, fake_list=None)

        # verify that the method will return True when the status of instance
        # is not in the expected status.
        result = nova_util.confirm_resize(instance, instance.status)
        self.assertTrue(result)

        # verify that the method will return False when the status of instance
        # is not in the expected status.
        result = nova_util.confirm_resize(instance, "fake_status")
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
