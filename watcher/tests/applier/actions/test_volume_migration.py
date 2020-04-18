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
from watcher.applier.actions import volume_migration
from watcher.common import cinder_helper
from watcher.common import clients
from watcher.common import keystone_helper
from watcher.common import nova_helper
from watcher.common import utils as w_utils
from watcher.tests import base


class TestMigration(base.TestCase):

    VOLUME_UUID = "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba"
    INSTANCE_UUID = "45a37aec-85ab-4dda-a303-7d9f62c2f5bb"

    def setUp(self):
        super(TestMigration, self).setUp()

        self.m_osc_cls = mock.Mock()
        self.m_osc = mock.Mock(spec=clients.OpenStackClients)
        self.m_osc_cls.return_value = self.m_osc

        self.m_n_helper_cls = mock.Mock()
        self.m_n_helper = mock.Mock(spec=nova_helper.NovaHelper)
        self.m_n_helper_cls.return_value = self.m_n_helper

        self.m_c_helper_cls = mock.Mock()
        self.m_c_helper = mock.Mock(spec=cinder_helper.CinderHelper)
        self.m_c_helper_cls.return_value = self.m_c_helper

        self.m_k_helper_cls = mock.Mock()
        self.m_k_helper = mock.Mock(spec=keystone_helper.KeystoneHelper)
        self.m_k_helper_cls.return_value = self.m_k_helper

        m_openstack_clients = mock.patch.object(
            clients, "OpenStackClients", self.m_osc_cls)
        m_nova_helper = mock.patch.object(
            nova_helper, "NovaHelper", self.m_n_helper_cls)

        m_cinder_helper = mock.patch.object(
            cinder_helper, "CinderHelper", self.m_c_helper_cls)

        m_keystone_helper = mock.patch.object(
            keystone_helper, "KeystoneHelper", self.m_k_helper_cls)

        m_openstack_clients.start()
        m_nova_helper.start()
        m_cinder_helper.start()
        m_keystone_helper.start()

        self.addCleanup(m_keystone_helper.stop)
        self.addCleanup(m_cinder_helper.stop)
        self.addCleanup(m_nova_helper.stop)
        self.addCleanup(m_openstack_clients.stop)

        self.action = volume_migration.VolumeMigrate(mock.Mock())

        self.input_parameters_swap = {
            "migration_type": "swap",
            "destination_node": "storage1-poolname",
            "destination_type": "storage1-typename",
            baction.BaseAction.RESOURCE_ID: self.VOLUME_UUID,
        }
        self.action_swap = volume_migration.VolumeMigrate(mock.Mock())
        self.action_swap.input_parameters = self.input_parameters_swap

        self.input_parameters_migrate = {
            "migration_type": "migrate",
            "destination_node": "storage1-poolname",
            "destination_type": "",
            baction.BaseAction.RESOURCE_ID: self.VOLUME_UUID,
        }
        self.action_migrate = volume_migration.VolumeMigrate(mock.Mock())
        self.action_migrate.input_parameters = self.input_parameters_migrate

        self.input_parameters_retype = {
            "migration_type": "retype",
            "destination_node": "",
            "destination_type": "storage1-typename",
            baction.BaseAction.RESOURCE_ID: self.VOLUME_UUID,
        }
        self.action_retype = volume_migration.VolumeMigrate(mock.Mock())
        self.action_retype.input_parameters = self.input_parameters_retype

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock()
        volume.id = kwargs.get('id', TestMigration.VOLUME_UUID)
        volume.size = kwargs.get('size', '1')
        volume.status = kwargs.get('status', 'available')
        volume.snapshot_id = kwargs.get('snapshot_id', None)
        volume.availability_zone = kwargs.get('availability_zone', 'nova')
        return volume

    @staticmethod
    def fake_instance(**kwargs):
        instance = mock.MagicMock()
        instance.id = kwargs.get('id', TestMigration.INSTANCE_UUID)
        instance.status = kwargs.get('status', 'ACTIVE')
        return instance

    def test_parameters_swap(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.VOLUME_UUID,
                  self.action.MIGRATION_TYPE: 'swap',
                  self.action.DESTINATION_NODE: None,
                  self.action.DESTINATION_TYPE: 'type-1'}
        self.action_swap.input_parameters = params
        self.assertTrue(self.action_swap.validate_parameters)

    def test_parameters_migrate(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.VOLUME_UUID,
                  self.action.MIGRATION_TYPE: 'migrate',
                  self.action.DESTINATION_NODE: 'node-1',
                  self.action.DESTINATION_TYPE: None}
        self.action_migrate.input_parameters = params
        self.assertTrue(self.action_migrate.validate_parameters)

    def test_parameters_retype(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.VOLUME_UUID,
                  self.action.MIGRATION_TYPE: 'retype',
                  self.action.DESTINATION_NODE: None,
                  self.action.DESTINATION_TYPE: 'type-1'}
        self.action_retype.input_parameters = params
        self.assertTrue(self.action_retype.validate_parameters)

    def test_parameters_exception_resource_id(self):
        params = {baction.BaseAction.RESOURCE_ID: "EFEF",
                  self.action.MIGRATION_TYPE: 'swap',
                  self.action.DESTINATION_NODE: None,
                  self.action.DESTINATION_TYPE: 'type-1'}
        self.action_swap.input_parameters = params
        self.assertRaises(jsonschema.ValidationError,
                          self.action_swap.validate_parameters)

    def test_migrate_success(self):
        volume = self.fake_volume()

        self.m_c_helper.get_volume.return_value = volume
        result = self.action_migrate.execute()
        self.assertTrue(result)
        self.m_c_helper.migrate.assert_called_once_with(
            volume,
            "storage1-poolname"
        )

    def test_retype_success(self):
        volume = self.fake_volume()

        self.m_c_helper.get_volume.return_value = volume
        result = self.action_retype.execute()
        self.assertTrue(result)
        self.m_c_helper.retype.assert_called_once_with(
            volume,
            "storage1-typename",
        )

    def test_swap_success(self):
        volume = self.fake_volume(
            status='in-use', attachments=[{'server_id': 'server_id'}])
        self.m_n_helper.find_instance.return_value = self.fake_instance()

        new_volume = self.fake_volume(id=w_utils.generate_uuid())
        user = mock.Mock()
        session = mock.MagicMock()
        self.m_k_helper.create_user.return_value = user
        self.m_k_helper.create_session.return_value = session
        self.m_c_helper.get_volume.return_value = volume
        self.m_c_helper.create_volume.return_value = new_volume

        result = self.action_swap.execute()
        self.assertTrue(result)

        self.m_n_helper.swap_volume.assert_called_once_with(
            volume,
            new_volume
        )
        self.m_k_helper.delete_user.assert_called_once_with(user)

    def test_swap_fail(self):
        # _can_swap fail
        instance = self.fake_instance(status='STOPPED')
        self.m_n_helper.find_instance.return_value = instance

        result = self.action_swap.execute()
        self.assertFalse(result)

    def test_can_swap_success(self):
        volume = self.fake_volume(
            status='in-use', attachments=[{'server_id': 'server_id'}])
        instance = self.fake_instance()

        self.m_n_helper.find_instance.return_value = instance
        result = self.action_swap._can_swap(volume)
        self.assertTrue(result)

        instance = self.fake_instance(status='PAUSED')
        self.m_n_helper.find_instance.return_value = instance
        result = self.action_swap._can_swap(volume)
        self.assertTrue(result)

        instance = self.fake_instance(status='RESIZED')
        self.m_n_helper.find_instance.return_value = instance
        result = self.action_swap._can_swap(volume)
        self.assertTrue(result)

    def test_can_swap_fail(self):

        volume = self.fake_volume(
            status='in-use', attachments=[{'server_id': 'server_id'}])
        instance = self.fake_instance(status='STOPPED')
        self.m_n_helper.find_instance.return_value = instance
        result = self.action_swap._can_swap(volume)
        self.assertFalse(result)
