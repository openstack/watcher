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

import fixtures
import jsonschema

from watcher.applier.actions import base as baction
from watcher.applier.actions import volume_migration
from watcher.common import cinder_helper
from watcher.common import exception
from watcher.common import nova_helper
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils


class TestMigration(
    test_utils.CinderResourcesMixin,
    test_utils.NovaResourcesMixin,
    base.TestCase,
):
    VOLUME_UUID = "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba"
    INSTANCE_UUID = "45a37aec-85ab-4dda-a303-7d9f62c2f5bb"

    def setUp(self):
        super().setUp()

        self.m_n_helper = self.useFixture(
            fixtures.MockPatch(
                "watcher.common.nova_helper.NovaHelper", autospec=False
            )
        ).mock.return_value

        self.m_c_helper = self.useFixture(
            fixtures.MockPatch(
                "watcher.common.cinder_helper.CinderHelper", autospec=False
            )
        ).mock.return_value

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

    def _create_volume(self, **kwargs):
        kwargs.setdefault('id', self.VOLUME_UUID)
        kwargs.setdefault('volume_type', 'default-type')
        kwargs.setdefault('host', 'current-host')
        return cinder_helper.Volume.from_openstacksdk(
            self.create_openstacksdk_volume(**kwargs)
        )

    def _create_instance(self, **kwargs):
        kwargs.setdefault('id', self.INSTANCE_UUID)
        return nova_helper.Server.from_openstacksdk(
            self.create_openstacksdk_server(**kwargs)
        )

    def test_parameters_swap(self):
        params = {
            baction.BaseAction.RESOURCE_ID: self.VOLUME_UUID,
            self.action.MIGRATION_TYPE: 'swap',
            self.action.DESTINATION_NODE: None,
            self.action.DESTINATION_TYPE: 'type-1',
        }
        self.action_swap.input_parameters = params
        self.assertTrue(self.action_swap.validate_parameters)

    def test_parameters_migrate(self):
        params = {
            baction.BaseAction.RESOURCE_ID: self.VOLUME_UUID,
            self.action.MIGRATION_TYPE: 'migrate',
            self.action.DESTINATION_NODE: 'node-1',
            self.action.DESTINATION_TYPE: None,
        }
        self.action_migrate.input_parameters = params
        self.assertTrue(self.action_migrate.validate_parameters)

    def test_parameters_retype(self):
        params = {
            baction.BaseAction.RESOURCE_ID: self.VOLUME_UUID,
            self.action.MIGRATION_TYPE: 'retype',
            self.action.DESTINATION_NODE: None,
            self.action.DESTINATION_TYPE: 'type-1',
        }
        self.action_retype.input_parameters = params
        self.assertTrue(self.action_retype.validate_parameters)

    def test_parameters_exception_resource_id(self):
        params = {
            baction.BaseAction.RESOURCE_ID: "EFEF",
            self.action.MIGRATION_TYPE: 'swap',
            self.action.DESTINATION_NODE: None,
            self.action.DESTINATION_TYPE: 'type-1',
        }
        self.action_swap.input_parameters = params
        self.assertRaises(
            jsonschema.ValidationError, self.action_swap.validate_parameters
        )

    def test_migrate_success(self):
        volume = self._create_volume()

        self.m_c_helper.get_volume.return_value = volume
        result = self.action_migrate.execute()
        self.assertTrue(result)
        self.m_c_helper.migrate.assert_called_once_with(
            volume, "storage1-poolname"
        )

    def test_retype_success(self):
        volume = self._create_volume()

        self.m_c_helper.get_volume.return_value = volume
        result = self.action_retype.execute()
        self.assertTrue(result)
        self.m_c_helper.retype.assert_called_once_with(
            volume, "storage1-typename"
        )

    def test_can_swap_success(self):
        volume = self._create_volume(
            status='in-use', attachments=[{'server_id': self.INSTANCE_UUID}]
        )

        instance = self._create_instance()
        self.m_n_helper.find_instance.return_value = instance

        result = self.action_swap._can_swap(volume)
        self.assertTrue(result)

        instance = self._create_instance(status='PAUSED')
        self.m_n_helper.find_instance.return_value = instance
        result = self.action_swap._can_swap(volume)
        self.assertTrue(result)

    def test_can_swap_fail(self):
        volume = self._create_volume(
            status='in-use', attachments=[{'server_id': self.INSTANCE_UUID}]
        )
        instance = self._create_instance(status='STOPPED')
        self.m_n_helper.find_instance.return_value = instance
        result = self.action_swap._can_swap(volume)
        self.assertFalse(result)

        instance = self._create_instance(status='RESIZED')
        self.m_n_helper.find_instance.return_value = instance
        result = self.action_swap._can_swap(volume)
        self.assertFalse(result)

    def test_can_swap_instance_not_found(self):
        volume = self._create_volume(
            status='in-use', attachments=[{'server_id': self.INSTANCE_UUID}]
        )
        self.m_n_helper.find_instance.side_effect = (
            exception.ComputeResourceNotFound(self.INSTANCE_UUID)
        )
        result = self.action_swap._can_swap(volume)
        self.assertFalse(result)

    def test_swap_success(self):
        volume = self._create_volume(
            status='in-use', attachments=[{'server_id': self.INSTANCE_UUID}]
        )
        self.m_c_helper.get_volume.return_value = volume

        instance = self._create_instance()
        self.m_n_helper.find_instance.return_value = instance

        result = self.action_swap.execute()
        self.assertTrue(result)
        self.m_c_helper.migrate.assert_called_once_with(
            volume, "storage1-poolname"
        )

    def test_pre_condition_volume_not_found(self):
        err = exception.StorageResourceNotFound()
        self.m_c_helper.get_volume.side_effect = err

        # ActionSkipped is expected because the volume is not found
        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Volume {self.VOLUME_UUID} not found",
            self.action_migrate.pre_condition,
        )

    def test_pre_condition_destination_type_not_found(self):
        volume = self._create_volume()
        self.m_c_helper.get_volume.return_value = volume

        # Mock volume type list that doesn't contain the destination type
        fake_type_1 = cinder_helper.VolumeType.from_openstacksdk(
            self.create_openstacksdk_volume_type(name="type-1")
        )
        fake_type_2 = cinder_helper.VolumeType.from_openstacksdk(
            self.create_openstacksdk_volume_type(name="type-2")
        )
        self.m_c_helper.get_volume_type_list.return_value = [
            fake_type_1,
            fake_type_2,
        ]

        # ActionExecutionFailure is expected because the destination type
        # is not found
        self.assertRaisesRegex(
            exception.ActionExecutionFailure,
            "Volume type storage1-typename not found",
            self.action_retype.pre_condition,
        )

    def test_pre_condition_destination_pool_not_found(self):
        volume = self._create_volume()
        self.m_c_helper.get_volume.return_value = volume

        # Mock get_storage_pool_by_name to raise PoolNotFound
        self.m_c_helper.get_storage_pool_by_name.side_effect = (
            exception.PoolNotFound(name="storage1-poolname")
        )

        # ActionExecutionFailure is expected because the destination pool
        # is not found
        self.assertRaisesRegex(
            exception.ActionExecutionFailure,
            "Pool storage1-poolname not found",
            self.action_migrate.pre_condition,
        )

    def test_pre_condition_success_with_type(self):
        volume = self._create_volume()
        self.m_c_helper.get_volume.return_value = volume

        # Mock volume type list that contains the destination type
        fake_type_1 = cinder_helper.VolumeType.from_openstacksdk(
            self.create_openstacksdk_volume_type(name="storage1-typename")
        )
        fake_type_2 = cinder_helper.VolumeType.from_openstacksdk(
            self.create_openstacksdk_volume_type(name="type-2")
        )
        self.m_c_helper.get_volume_type_list.return_value = [
            fake_type_1,
            fake_type_2,
        ]

        # Should not raise any exception
        self.action_retype.pre_condition()
        self.m_c_helper.get_volume.assert_called_once_with(self.VOLUME_UUID)
        self.m_c_helper.get_volume_type_list.assert_called_once_with()

    def test_pre_condition_success_with_pool(self):
        volume = self._create_volume()
        self.m_c_helper.get_volume.return_value = volume

        # Mock pool
        fake_pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(name="storage1-poolname")
        )
        self.m_c_helper.get_storage_pool_by_name.return_value = fake_pool

        # Should not raise any exception
        self.action_migrate.pre_condition()
        self.m_c_helper.get_volume.assert_called_once_with(self.VOLUME_UUID)
        self.m_c_helper.get_storage_pool_by_name.assert_called_once_with(
            "storage1-poolname"
        )

    def test_pre_condition_retype_same_type(self):
        # Create volume with the same type as destination
        volume = self._create_volume(volume_type="storage1-typename")
        self.m_c_helper.get_volume.return_value = volume

        # Mock volume type list that contains the destination type
        fake_type = cinder_helper.VolumeType.from_openstacksdk(
            self.create_openstacksdk_volume_type(name="storage1-typename")
        )
        self.m_c_helper.get_volume_type_list.return_value = [fake_type]

        # ActionSkipped is expected because volume already has the target type
        self.assertRaisesRegex(
            exception.ActionSkipped,
            "Volume type is already storage1-typename",
            self.action_retype.pre_condition,
        )

    def test_pre_condition_migrate_same_node(self):
        # Create volume on the same node as destination
        volume = self._create_volume(host="storage1-poolname")
        self.m_c_helper.get_volume.return_value = volume

        # Mock pool
        fake_pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(name="storage1-poolname")
        )
        self.m_c_helper.get_storage_pool_by_name.return_value = fake_pool

        # ActionSkipped is expected because volume is already on target node
        self.assertRaisesRegex(
            exception.ActionSkipped,
            "Volume is already on node storage1-poolname",
            self.action_migrate.pre_condition,
        )
