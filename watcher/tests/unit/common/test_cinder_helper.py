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

import dataclasses as dc
import time

from unittest import mock

import fixtures

from openstack import exceptions as sdk_exc

from watcher import conf
from watcher.common import cinder_helper
from watcher.common import exception
from watcher.common import utils
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils


CONF = conf.CONF


class TestCinderHelper(test_utils.CinderResourcesMixin, base.TestCase):
    def setUp(self):
        super().setUp()
        self.mock_connection = self.useFixture(
            fixtures.MockPatch("watcher.common.clients.get_sdk_connection")
        ).mock.return_value

    def test_get_storage_node_list(self):
        node1 = self.create_openstacksdk_storage_service()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.services.return_value = [node1]
        cinder_util.get_storage_node_list()
        self.mock_connection.block_storage.services.assert_called_once_with(
            binary='cinder-volume'
        )

    def test_get_storage_node_by_name_success(self):
        node1 = self.create_openstacksdk_storage_service()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.services.return_value = [node1]
        node = cinder_util.get_storage_node_by_name('host@backend')

        self.assertEqual(node.host, 'host@backend')

    def test_get_storage_node_by_name_failure(self):
        node1 = self.create_openstacksdk_storage_service()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.services.return_value = [node1]
        self.assertRaisesRegex(
            exception.StorageNodeNotFound,
            "The storage node failure could not be found",
            cinder_util.get_storage_node_by_name,
            'failure',
        )

    def test_get_storage_pool_list(self):
        pool = self.create_openstacksdk_pool()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.backend_pools.return_value = [pool]
        cinder_util.get_storage_pool_list()
        self.mock_connection.block_storage.backend_pools.assert_called_once_with()

    def test_get_storage_pool_by_name_success(self):
        pool1 = self.create_openstacksdk_pool()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.backend_pools.return_value = [pool1]
        pool = cinder_util.get_storage_pool_by_name('host@backend#pool')

        self.assertEqual(pool.name, 'host@backend#pool')

    def test_get_storage_pool_by_name_failure(self):
        pool1 = self.create_openstacksdk_pool()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.backend_pools.return_value = [pool1]
        self.assertRaisesRegex(
            exception.PoolNotFound,
            "The pool failure could not be found",
            cinder_util.get_storage_pool_by_name,
            'failure',
        )

    def test_get_volume_type_list(self):
        volume_type1 = self.create_openstacksdk_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.types.return_value = [volume_type1]
        cinder_util.get_volume_type_list()
        self.mock_connection.block_storage.types.assert_called_once_with()

    def test_get_volume_type_by_backendname_with_backend_exist(self):
        volume_type1 = self.create_openstacksdk_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.types.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'backend'
        )

        self.assertEqual(volume_type_name[0], volume_type1.name)

    def test_get_volume_type_by_backendname_with_no_backend_exist(self):
        volume_type1 = self.create_openstacksdk_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.types.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'nobackend'
        )

        self.assertEqual([], volume_type_name)

    def test_get_volume_type_name_by_id_found(self):
        volume_type1 = self.create_openstacksdk_volume_type(
            id='abc-123', name='my_type'
        )
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.get_type.return_value = volume_type1
        result = cinder_util.get_volume_type_name_by_id('abc-123')
        self.assertEqual('my_type', result)

    def test_get_volume_type_name_by_id_not_found(self):
        cinder_util = cinder_helper.CinderHelper()
        self.mock_connection.block_storage.get_type.side_effect = (
            sdk_exc.NotFoundException()
        )
        self.assertRaises(
            exception.VolumeTypeNotFound,
            cinder_util.get_volume_type_name_by_id,
            'unknown-id',
        )

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_pool_by_name')
    def test_migrate_success(self, mock_get_pool):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume(
            host='source_node', migration_status='success'
        )
        self.mock_connection.block_storage.get_volume.return_value = volume

        volume_type = self.create_openstacksdk_volume_type()
        self.mock_connection.block_storage.types.return_value = [volume_type]
        mock_pool = self.create_openstacksdk_pool()
        mock_get_pool.return_value = mock_pool

        result = cinder_util.migrate(volume, 'host@backend#pool')
        mock_get_pool.assert_called_once_with('host@backend#pool')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_pool_by_name')
    def test_migrate_fail(self, mock_get_pool):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()
        self.mock_connection.block_storage.get_volume.return_value = volume
        mock_pool = self.create_openstacksdk_pool()
        mock_get_pool.return_value = mock_pool

        volume_type = self.create_openstacksdk_volume_type(
            name='notbackend',
            extra_specs={'volume_backend_name': 'diff_backend'},
        )
        self.mock_connection.block_storage.types.return_value = [volume_type]

        self.assertRaisesRegex(
            exception.Invalid,
            "Volume type 'fake_type' is not compatible "
            "with destination pool 'host@backend#pool'",
            cinder_util.migrate,
            volume,
            'host@backend#pool',
        )

        volume = self.create_openstacksdk_volume(
            migration_status='error', host='source_node'
        )
        self.mock_connection.block_storage.get_volume.return_value = volume

        # check that a volume type without any
        # volume_backend_name passes the volume type check
        # and proceeds to the migration
        volume_type = self.create_openstacksdk_volume_type(extra_specs={})
        self.mock_connection.block_storage.types.return_value = [volume_type]

        result = cinder_util.migrate(volume, 'host@backend#pool')
        mock_get_pool.assert_called_with('host@backend#pool')
        self.mock_connection.block_storage.migrate_volume.assert_called_with(
            volume.id,
            host='host@backend#pool',
            force_host_copy=False,
            lock_volume=True,
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    def test_retype_success(self, mock_get_volume):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()

        def side_effect(volume, status, volume_type):
            return cinder_helper.Volume.from_openstacksdk(
                self.create_openstacksdk_volume(
                    status=status, volume_type=volume_type
                )
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'in-use', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'notfake_type'),
            side_effect(volume, 'in-use', 'notfake_type'),
        ]
        self.mock_connection.block_storage.get_volume.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_retype_fail(self):
        cinder_util = cinder_helper.CinderHelper()

        # dest_type is the actual one
        volume = self.create_openstacksdk_volume(
            host='source_node', migration_status='success'
        )
        self.mock_connection.block_storage.get_volume.return_value = volume

        self.assertRaisesRegex(
            exception.Invalid,
            "Volume type must be different for retyping",
            cinder_util.retype,
            volume,
            'fake_type',
        )

        # type is not the expected one
        volume = self.create_openstacksdk_volume()
        self.mock_connection.block_storage.get_volume.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertFalse(result)

        # type is correct but status is error
        volume = self.create_openstacksdk_volume(status='error')
        self.mock_connection.block_storage.get_volume.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_can_get_volume_success(self):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()
        cinder_util.get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util._can_get_volume(volume.id)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_can_get_volume_fail(self):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()
        cinder_util.get_volume = mock.MagicMock()
        cinder_util.get_volume.side_effect = (
            exception.StorageResourceNotFound()
        )
        result = cinder_util._can_get_volume(volume.id)
        self.assertFalse(result)

    def test_can_get_volume_not_found_via_decorator(self):
        """_can_get_volume returns False through the decorator path."""
        cinder_util = cinder_helper.CinderHelper()
        err = sdk_exc.NotFoundException()
        self.mock_connection.block_storage.get_volume.side_effect = err

        self.mock_connection.block_storage.find_volume.side_effect = err
        result = cinder_util._can_get_volume('missing-vol')
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_get_volume_success(self):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()
        self.mock_connection.block_storage.get_volume.return_value = volume
        result = cinder_util.get_volume(volume)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_get_volume_fail(self):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()
        side_effect = sdk_exc.NotFoundException()
        self.mock_connection.block_storage.get_volume.side_effect = side_effect
        found = self.create_openstacksdk_volume(name='found_by_name')
        self.mock_connection.block_storage.find_volume.return_value = found
        result = cinder_util.get_volume(volume)
        self.assertEqual(result.name, 'found_by_name')

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_volume_deleted_success(self):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()
        self.mock_connection.block_storage.get_volume.return_value = volume
        cinder_util._can_get_volume = mock.MagicMock(return_value=None)
        result = cinder_util.check_volume_deleted(
            volume, retry=2, retry_interval=1
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_volume_deleted_fail(self):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume()
        self.mock_connection.block_storage.get_volume.return_value = volume
        cinder_util._can_get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_volume_deleted(
            volume, retry=2, retry_interval=1
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_migrated_success(self):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume(
            migration_status='success', host='host@backend#pool'
        )
        self.mock_connection.block_storage.get_volume.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_migrated(volume)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_migrated_fail(self):
        def side_effect(volume):
            if isinstance(volume, str):
                return cinder_helper.Volume.from_openstacksdk(
                    self.create_openstacksdk_volume(
                        migration_status='error', host='source_node'
                    )
                )
            elif volume.id is None:
                return cinder_helper.Volume.from_openstacksdk(
                    self.create_openstacksdk_volume(
                        migration_status='fake_status',
                        id=utils.generate_uuid(),
                    )
                )
            return cinder_helper.Volume.from_openstacksdk(volume)

        cinder_util = cinder_helper.CinderHelper()

        # verify that the method check_migrated will
        # return False when the status of migration_status
        # is error.
        volume = self.create_openstacksdk_volume(
            migration_status='error', host='source_node'
        )
        self.mock_connection.block_storage.get_volume.return_value = volume
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

        # verify that the method check_migrated will
        # return False when the status of migration_status
        # is in other cases.
        volume = self.create_openstacksdk_volume(
            migration_status='success', host='source_node', id=None
        )
        cinder_util.get_volume = mock.MagicMock()
        cinder_util.get_volume.side_effect = side_effect
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

        # verify that the method check_migrated will
        # return False when the return_value of method
        # check_volume_deleted is False.
        volume = self.create_openstacksdk_volume(
            migration_status='success', host='source_node'
        )
        self.mock_connection.block_storage.get_volume.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=False)
        cinder_util.get_deleting_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.LOG, 'debug')
    def test_check_retyped_success_immediate(self, mock_log_debug):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_openstacksdk_volume(
            status='in-use', volume_type='dest_type'
        )
        self.mock_connection.block_storage.get_volume.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_retyped(volume, 'dest_type')
        self.assertNotIn(
            mock.call('Waiting the retype of %s', volume),
            mock_log_debug.mock_calls,
        )
        mock_log_debug.assert_called_with(
            "Volume retype succeeded : volume %(volume)s "
            "has now type '%(type)s'.",
            {'volume': volume.id, 'type': 'dest_type'},
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    def test_check_retyped_success_retries(
        self, mock_log_debug, mock_get_volume
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_openstacksdk_volume(status='in-use')

        def side_effect(volume, status, volume_type):
            return cinder_helper.Volume.from_openstacksdk(
                self.create_openstacksdk_volume(
                    status=status, volume_type=volume_type
                )
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'dest_type'),
        ]

        wrap_vol = cinder_helper.Volume.from_openstacksdk(volume)
        self.mock_connection.block_storage.get_volume.return_value = wrap_vol
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_retyped(volume, 'dest_type')
        self.assertEqual(mock_get_volume.call_count, 3)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_debug.assert_called_with(
            "Volume retype succeeded : volume %(volume)s "
            "has now type '%(type)s'.",
            {'volume': volume.id, 'type': 'dest_type'},
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    def test_check_retyped_success_retries_migration(
        self, mock_log_debug, mock_get_volume
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_openstacksdk_volume(
            status='in-use', migration_status='success', host='source_node'
        )

        def side_effect(volume, status, volume_type):
            return cinder_helper.Volume.from_openstacksdk(
                self.create_openstacksdk_volume(
                    status=status, volume_type=volume_type
                )
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'dest_type'),
        ]

        self.mock_connection.block_storage.get_volume.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        cinder_util.get_deleting_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_retyped(volume, 'dest_type')
        self.assertEqual(mock_get_volume.call_count, 3)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_debug.assert_called_with(
            "Volume retype succeeded : volume %(volume)s "
            "has now type '%(type)s'.",
            {'volume': volume.id, 'type': 'dest_type'},
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    @mock.patch.object(cinder_helper.LOG, 'error')
    def test_check_retyped_failed_available(
        self, mock_log_error, mock_log_debug, mock_get_volume
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_openstacksdk_volume(status='available')

        def side_effect(volume, status, volume_type):
            return cinder_helper.Volume.from_openstacksdk(
                self.create_openstacksdk_volume(
                    status=status, volume_type=volume_type
                )
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'available', 'fake_type'),
        ]

        self.mock_connection.block_storage.get_volume.return_value = volume
        result = cinder_util.check_retyped(
            volume, 'dest_type', retry_interval=1
        )
        self.assertEqual(mock_get_volume.call_count, 3)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_error.assert_called_with(
            "Volume retype failed : volume %(volume)s "
            "has now type '%(type)s' and status %(status)s",
            {'volume': volume.id, 'type': 'fake_type', 'status': 'available'},
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    @mock.patch.object(cinder_helper.LOG, 'error')
    def test_check_retyped_failed_inuse(
        self, mock_log_error, mock_log_debug, mock_get_volume
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_openstacksdk_volume(
            status='in-use', migration_status='error'
        )

        def side_effect(volume, status, volume_type):
            return cinder_helper.Volume.from_openstacksdk(
                self.create_openstacksdk_volume(
                    status=status,
                    volume_type=volume_type,
                    migration_status='error',
                )
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'fake_type'),
        ]

        self.mock_connection.block_storage.get_volume.return_value = volume
        result = cinder_util.check_retyped(
            volume, 'dest_type', retry_interval=1
        )
        self.assertEqual(mock_get_volume.call_count, 4)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_error.assert_any_call(
            "Volume retype failed : volume %(volume)s "
            "has now type '%(type)s' and status %(status)s",
            {'volume': volume.id, 'type': 'fake_type', 'status': 'in-use'},
        )
        mock_log_error.assert_called_with(
            "Volume migration error on volume %(volume)s.",
            {'volume': volume.id},
        )
        self.assertFalse(result)

    def test_get_volume_types_for_pool_matching_backend(self):
        """Test matching backend and no extra_specs."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(
                name='host@backend#pool',
                capabilities={'volume_backend_name': 'backend'},
            )
        )
        volume_type1 = self.create_openstacksdk_volume_type(
            name='type_matching',
            extra_specs={'volume_backend_name': 'backend'},
        )
        volume_type2 = self.create_openstacksdk_volume_type(
            name='type_no_specs', extra_specs={}
        )
        self.mock_connection.block_storage.types.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(sorted(result), ['type_matching', 'type_no_specs'])

    def test_get_volume_types_for_pool_different_backend(self):
        """Test different backend excluded."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(
                name='host@backend#pool',
                capabilities={'volume_backend_name': 'backend'},
            )
        )
        volume_type1 = self.create_openstacksdk_volume_type(
            name='type_no_specs', extra_specs={}
        )
        volume_type2 = self.create_openstacksdk_volume_type(
            name='type_different_backend',
            extra_specs={'volume_backend_name': 'different_backend'},
        )
        self.mock_connection.block_storage.types.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_no_specs'])

    def test_get_volume_types_for_pool_matching_capability(self):
        """Test volume type with matching capability."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(
                name='host@backend#pool', capabilities={'disk_speed': 'fast'}
            )
        )
        volume_type = self.create_openstacksdk_volume_type(
            name='type_fast_disk', extra_specs={'disk_speed': 'fast'}
        )
        self.mock_connection.block_storage.types.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_fast_disk'])

    def test_get_volume_types_for_pool_mismatched_capability(self):
        """Test volume type with different capability."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(
                name='host@backend#pool', capabilities={'disk_speed': 'fast'}
            )
        )
        volume_type = self.create_openstacksdk_volume_type(
            name='type_slow_disk', extra_specs={'disk_speed': 'slow'}
        )
        self.mock_connection.block_storage.types.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual([], result)

    def test_get_volume_types_for_pool_no_capabilities(self):
        """Test pool with no capabilities."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(
                name='host@backend#pool', capabilities={}
            )
        )
        volume_type1 = self.create_openstacksdk_volume_type(
            name='type_no_specs', extra_specs={}
        )
        volume_type2 = self.create_openstacksdk_volume_type(
            name='type_with_specs',
            extra_specs={'volume_backend_name': 'backend'},
        )
        self.mock_connection.block_storage.types.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_no_specs', 'type_with_specs'])

    def test_get_volume_types_for_pool_requirements_not_in_caps(self):
        """Test vol type with reqs not in pool caps."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(
                name='host@backend#pool',
                capabilities={'volume_backend_name': 'backend'},
            )
        )
        volume_type = self.create_openstacksdk_volume_type(
            name='type_extra_reqs',
            extra_specs={
                'volume_backend_name': 'backend',
                'disk_speed': 'fast',
            },
        )
        self.mock_connection.block_storage.types.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_extra_reqs'])

    def test_get_volume_types_for_pool_multiple_specs_partial_match(self):
        """Test vol type with multiple extra_specs."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_openstacksdk(
            self.create_openstacksdk_pool(
                name='host@backend#pool',
                capabilities={
                    'volume_backend_name': 'backend',
                    'disk_speed': 'fast',
                    'compression': 'enabled',
                },
            )
        )
        volume_type = self.create_openstacksdk_volume_type(
            name='type_partial',
            extra_specs={
                'volume_backend_name': 'backend',
                'disk_speed': 'slow',
                'compression': 'enabled',
            },
        )
        self.mock_connection.block_storage.types.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual([], result)


class TestHandleCinderError(test_utils.CinderResourcesMixin, base.TestCase):
    """Tests for the handle_cinder_error decorator."""

    def setUp(self):
        super().setUp()
        self.mock_connection = self.useFixture(
            fixtures.MockPatch("watcher.common.clients.get_sdk_connection")
        ).mock.return_value

    def test_not_found_raises_storage_resource_not_found(self):
        cinder_util = cinder_helper.CinderHelper()
        err = sdk_exc.NotFoundException()
        self.mock_connection.block_storage.get_volume.side_effect = err
        self.mock_connection.block_storage.find_volume.side_effect = err
        self.assertRaises(
            exception.StorageResourceNotFound,
            cinder_util.get_volume,
            'missing-vol',
        )

    def test_client_exception_raises_cinder_client_error(self):
        cinder_util = cinder_helper.CinderHelper()
        err = sdk_exc.SDKException()
        self.mock_connection.block_storage.volumes.side_effect = err
        self.assertRaises(
            exception.CinderClientError, cinder_util.get_volume_list
        )

    def test_not_found_on_list_raises_storage_resource_not_found(self):
        cinder_util = cinder_helper.CinderHelper()
        err = sdk_exc.NotFoundException()
        self.mock_connection.block_storage.backend_pools.side_effect = err
        self.assertRaises(
            exception.StorageResourceNotFound,
            cinder_util.get_storage_pool_list,
        )


class TestStorageService(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the StorageService dataclass wrapper."""

    def test_from_openstacksdk(self):
        svc = self.create_openstacksdk_storage_service()
        result = cinder_helper.StorageService.from_openstacksdk(svc)
        self.assertEqual('host@backend', result.host)
        self.assertEqual('nova', result.availability_zone)
        self.assertEqual('up', result.state)
        self.assertEqual('enabled', result.status)

    def test_from_openstacksdk_custom_values(self):
        svc = self.create_openstacksdk_storage_service(
            host='node1@lvm',
            availability_zone='az1',
            state='down',
            status='disabled',
        )
        result = cinder_helper.StorageService.from_openstacksdk(svc)
        self.assertEqual('node1@lvm', result.host)
        self.assertEqual('az1', result.availability_zone)
        self.assertEqual('down', result.state)
        self.assertEqual('disabled', result.status)

    def test_frozen(self):
        svc = self.create_openstacksdk_storage_service()
        result = cinder_helper.StorageService.from_openstacksdk(svc)
        self.assertRaises(dc.FrozenInstanceError, setattr, result, 'host', 'x')

    def test_equality(self):
        svc = self.create_openstacksdk_storage_service()
        a = cinder_helper.StorageService.from_openstacksdk(svc)
        b = cinder_helper.StorageService.from_openstacksdk(svc)
        self.assertEqual(a, b)

    def test_inequality(self):
        svc1 = self.create_openstacksdk_storage_service(host='host1')
        svc2 = self.create_openstacksdk_storage_service(host='host2')
        a = cinder_helper.StorageService.from_openstacksdk(svc1)
        b = cinder_helper.StorageService.from_openstacksdk(svc2)
        self.assertNotEqual(a, b)


class TestStoragePool(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the StoragePool dataclass wrapper."""

    def test_from_openstacksdk_defaults(self):
        pool = self.create_openstacksdk_pool()
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertEqual('host@backend#pool', result.name)
        self.assertEqual('pool', result.pool_name)
        self.assertEqual(0, result.total_volumes)
        self.assertEqual(100.0, result.total_capacity_gb)
        self.assertEqual(50.0, result.free_capacity_gb)
        self.assertEqual(50.0, result.provisioned_capacity_gb)
        self.assertEqual(50.0, result.allocated_capacity_gb)
        self.assertEqual(1.0, result.max_over_subscription_ratio)
        self.assertEqual('backend', result.volume_backend_name)
        self.assertIsInstance(result.capabilities, dict)

    def test_from_openstacksdk_custom_values(self):
        pool = self.create_openstacksdk_pool(
            name='node1@ceph#ssd_pool',
            total_capacity_gb=500.0,
            free_capacity_gb=200.0,
            provisioned_capacity_gb=300.0,
            allocated_capacity_gb=250.0,
            total_volumes=42,
            max_over_subscription_ratio=2.0,
            volume_backend_name='ceph',
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertEqual('node1@ceph#ssd_pool', result.name)
        self.assertEqual('ssd_pool', result.pool_name)
        self.assertEqual(42, result.total_volumes)
        self.assertEqual(500.0, result.total_capacity_gb)
        self.assertEqual(200.0, result.free_capacity_gb)
        self.assertEqual(300.0, result.provisioned_capacity_gb)
        self.assertEqual(250.0, result.allocated_capacity_gb)
        self.assertEqual(2.0, result.max_over_subscription_ratio)
        self.assertEqual('ceph', result.volume_backend_name)

    def test_from_openstacksdk_unknown_capacities(self):
        """Capacity values of 'unknown' should become None."""
        pool = self.create_openstacksdk_pool(
            capabilities={
                'total_capacity_gb': 'unknown',
                'free_capacity_gb': 'unknown',
                'provisioned_capacity_gb': 'unknown',
                'allocated_capacity_gb': 'unknown',
            }
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertIsNone(result.total_capacity_gb)
        self.assertIsNone(result.free_capacity_gb)
        self.assertIsNone(result.provisioned_capacity_gb)
        self.assertIsNone(result.allocated_capacity_gb)

    def test_from_openstacksdk_none_capacities(self):
        """Capacity values of None should remain None."""
        pool = self.create_openstacksdk_pool(
            capabilities={
                'total_capacity_gb': None,
                'free_capacity_gb': None,
                'provisioned_capacity_gb': None,
                'allocated_capacity_gb': None,
            }
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertIsNone(result.total_capacity_gb)
        self.assertIsNone(result.free_capacity_gb)
        self.assertIsNone(result.provisioned_capacity_gb)
        self.assertIsNone(result.allocated_capacity_gb)

    def test_from_openstacksdk_mixed_capacities(self):
        """Mix of numeric, 'unknown', and None capacity values."""
        pool = self.create_openstacksdk_pool(
            capabilities={
                'total_capacity_gb': 100.0,
                'free_capacity_gb': 'unknown',
                'provisioned_capacity_gb': None,
                'allocated_capacity_gb': 25,
            }
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertEqual(100.0, result.total_capacity_gb)
        self.assertIsNone(result.free_capacity_gb)
        self.assertIsNone(result.provisioned_capacity_gb)
        self.assertEqual(25.0, result.allocated_capacity_gb)

    def test_from_openstacksdk_integer_capacities_become_float(self):
        """Integer capacity values should be converted to float."""
        pool = self.create_openstacksdk_pool(
            total_capacity_gb=100,
            free_capacity_gb=50,
            provisioned_capacity_gb=50,
            allocated_capacity_gb=50,
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertIsInstance(result.total_capacity_gb, float)
        self.assertIsInstance(result.free_capacity_gb, float)
        self.assertIsInstance(result.provisioned_capacity_gb, float)
        self.assertIsInstance(result.allocated_capacity_gb, float)

    def test_from_openstacksdk_capabilities_preserved(self):
        """Extra capabilities beyond standard fields are preserved."""
        pool = self.create_openstacksdk_pool(
            capabilities={
                'total_capacity_gb': 100.0,
                'free_capacity_gb': 50.0,
                'provisioned_capacity_gb': 50.0,
                'allocated_capacity_gb': 50.0,
                'volume_backend_name': 'backend',
                'disk_speed': 'fast',
            }
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertEqual('fast', result.capabilities.get('disk_speed'))

    def test_from_openstacksdk_only_nonstandard_capabilities(self):
        """Capabilities with only non-standard fields."""
        pool = self.create_openstacksdk_pool(
            capabilities={'custom_key': 'custom_value'}
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertEqual(
            result.capabilities,
            {
                'custom_key': 'custom_value',
                'max_over_subscription_ratio': 1.0,
                'pool_name': 'pool',
                'total_volumes': 0,
                'volume_backend_name': 'backend',
            },
        )
        self.assertAlmostEqual(100.0, result.total_capacity_gb)
        self.assertAlmostEqual(50.0, result.free_capacity_gb)
        self.assertAlmostEqual(50.0, result.provisioned_capacity_gb)
        self.assertAlmostEqual(50.0, result.allocated_capacity_gb)

    def test_not_frozen_allows_mutation(self):
        """StoragePool is not frozen, allowing field mutation."""
        pool = self.create_openstacksdk_pool()
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        result.free_capacity_gb = 25.0
        self.assertEqual(25.0, result.free_capacity_gb)

    def test_from_openstacksdk_no_pool_name(self):
        """Pool without '#' in name should have pool_name from dict."""
        pool = self.create_openstacksdk_pool(
            name='host@backend', pool_name='mypool'
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertEqual('host@backend', result.name)
        self.assertEqual('mypool', result.pool_name)

    def test_from_openstacksdk_missing_optional_fields(self):
        """Missing optional fields use defaults."""
        pool = self.create_openstacksdk_pool(
            capabilities={
                'total_capacity_gb': 100.0,
                'free_capacity_gb': 50.0,
                'provisioned_capacity_gb': 50.0,
                'allocated_capacity_gb': 50.0,
            }
        )
        result = cinder_helper.StoragePool.from_openstacksdk(pool)
        self.assertIsNotNone(result.name)


class TestVolume(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the Volume dataclass wrapper."""

    def test_from_openstacksdk_defaults(self):
        vol = self.create_openstacksdk_volume()
        result = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertEqual('d010ef1f-dc19-4982-9383-087498bfde03', result.id)
        self.assertEqual('test-volume', result.name)
        self.assertEqual(1, result.size)
        self.assertEqual('available', result.status)
        self.assertEqual('fake_type', result.volume_type)
        self.assertEqual([], result.attachments)
        self.assertFalse(result.multiattach)
        self.assertEqual({}, result.metadata)
        self.assertEqual('false', result.bootable)
        self.assertEqual('2026-01-09T12:00:00', result.created_at)
        self.assertIsNone(result.host)
        self.assertIsNone(result.migration_status)
        self.assertIsNone(result.mig_name_id)
        self.assertIsNone(result.snapshot_id)

    def test_from_openstacksdk_custom_values(self):
        vol = self.create_openstacksdk_volume(
            id='d010ef1f-dc19-4982-9383-087498bfde06',
            name='my-volume',
            size=50,
            status='in-use',
            volume_type='ssd',
            attachments=[{'server_id': 'srv-1'}],
            multiattach=True,
            metadata={'key': 'value'},
            bootable='true',
            created_at='2026-06-15T10:00:00',
            host='node1@lvm#pool1',
            migration_status='success',
            mig_name_id='name-id-123',
            snapshot_id='snap-456',
            project_id='tenant-789',
        )
        result = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertEqual('d010ef1f-dc19-4982-9383-087498bfde06', result.id)
        self.assertEqual('my-volume', result.name)
        self.assertEqual(50, result.size)
        self.assertEqual('in-use', result.status)
        self.assertEqual('ssd', result.volume_type)
        self.assertEqual([{'server_id': 'srv-1'}], result.attachments)
        self.assertTrue(result.multiattach)
        self.assertEqual({'key': 'value'}, result.metadata)
        self.assertEqual('true', result.bootable)
        self.assertEqual('2026-06-15T10:00:00', result.created_at)
        self.assertEqual('node1@lvm#pool1', result.host)
        self.assertEqual('success', result.migration_status)
        self.assertEqual('name-id-123', result.mig_name_id)
        self.assertEqual('snap-456', result.snapshot_id)
        self.assertEqual('tenant-789', result.project_id)

    def test_from_openstacksdk_hyphenated_attrs(self):
        """Hyphenated cinderclient attrs are mapped correctly."""
        vol = self.create_openstacksdk_volume(
            host='host@backend#pool',
            project_id='project-abc',
            mig_name_id='name-id-xyz',
        )
        result = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertEqual('host@backend#pool', result.host)
        self.assertEqual('project-abc', result.project_id)
        self.assertEqual('name-id-xyz', result.mig_name_id)

    def test_frozen(self):
        vol = self.create_openstacksdk_volume()
        result = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertRaises(
            dc.FrozenInstanceError, setattr, result, 'status', 'x'
        )

    def test_equality(self):
        vol = self.create_openstacksdk_volume()
        a = cinder_helper.Volume.from_openstacksdk(vol)
        b = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertEqual(a, b)

    def test_with_none_optional_fields(self):
        """All optional fields can be None."""
        vol = self.create_openstacksdk_volume(
            host=None,
            migration_status=None,
            mig_name_id=None,
            snapshot_id=None,
            project_id=None,
        )
        result = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertIsNone(result.host)
        self.assertIsNone(result.migration_status)
        self.assertIsNone(result.mig_name_id)
        self.assertIsNone(result.snapshot_id)
        self.assertIsNone(result.project_id)

    def test_with_multiple_attachments(self):
        attachments = [
            {'server_id': 'srv-1', 'device': '/dev/vdb'},
            {'server_id': 'srv-2', 'device': '/dev/vdc'},
        ]
        vol = self.create_openstacksdk_volume(attachments=attachments)
        result = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertEqual(2, len(result.attachments))
        self.assertEqual('srv-1', result.attachments[0]['server_id'])
        self.assertEqual('srv-2', result.attachments[1]['server_id'])

    def test_with_metadata(self):
        metadata = {'env': 'prod', 'app': 'web'}
        vol = self.create_openstacksdk_volume(metadata=metadata)
        result = cinder_helper.Volume.from_openstacksdk(vol)
        self.assertEqual('prod', result.metadata['env'])
        self.assertEqual('web', result.metadata['app'])


class TestVolumeType(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the VolumeType dataclass wrapper."""

    def test_from_openstacksdk_defaults(self):
        vt = self.create_openstacksdk_volume_type()
        result = cinder_helper.VolumeType.from_openstacksdk(vt)
        self.assertEqual('a1b2c3d4-e5f6-7890-abcd-ef1234567890', result.id)
        self.assertEqual('fake_type', result.name)
        self.assertEqual(
            {'volume_backend_name': 'backend'}, result.extra_specs
        )

    def test_from_openstacksdk_custom_values(self):
        vt = self.create_openstacksdk_volume_type(
            id='b2c3d4e5-f6a7-8901-bcde-f12345678901',
            name='ssd-type',
            extra_specs={'volume_backend_name': 'ceph', 'disk_speed': 'fast'},
        )
        result = cinder_helper.VolumeType.from_openstacksdk(vt)
        self.assertEqual('b2c3d4e5-f6a7-8901-bcde-f12345678901', result.id)
        self.assertEqual('ssd-type', result.name)
        self.assertEqual('ceph', result.extra_specs['volume_backend_name'])
        self.assertEqual('fast', result.extra_specs['disk_speed'])

    def test_from_openstacksdk_empty_extra_specs(self):
        vt = self.create_openstacksdk_volume_type(
            name='generic', extra_specs={}
        )
        result = cinder_helper.VolumeType.from_openstacksdk(vt)
        self.assertEqual('generic', result.name)
        self.assertEqual({}, result.extra_specs)

    def test_frozen(self):
        vt = self.create_openstacksdk_volume_type()
        result = cinder_helper.VolumeType.from_openstacksdk(vt)
        self.assertRaises(dc.FrozenInstanceError, setattr, result, 'name', 'x')

    def test_equality(self):
        vt = self.create_openstacksdk_volume_type()
        a = cinder_helper.VolumeType.from_openstacksdk(vt)
        b = cinder_helper.VolumeType.from_openstacksdk(vt)
        self.assertEqual(a, b)


class TestVolumeSnapshot(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the VolumeSnapshot dataclass wrapper."""

    def test_from_openstacksdk_defaults(self):
        snap = self.create_openstacksdk_volume_snapshot()
        result = cinder_helper.VolumeSnapshot.from_openstacksdk(snap)
        self.assertEqual(
            'd010ef1f-dc19-4982-9383-087498bfde03', result.volume_id
        )

    def test_from_openstacksdk_custom_volume_id(self):
        snap = self.create_openstacksdk_volume_snapshot(
            volume_id='custom-vol-id'
        )
        result = cinder_helper.VolumeSnapshot.from_openstacksdk(snap)
        self.assertEqual('custom-vol-id', result.volume_id)

    def test_frozen(self):
        snap = self.create_openstacksdk_volume_snapshot()
        result = cinder_helper.VolumeSnapshot.from_openstacksdk(snap)
        self.assertRaises(
            dc.FrozenInstanceError, setattr, result, 'volume_id', 'x'
        )

    def test_equality(self):
        snap = self.create_openstacksdk_volume_snapshot()
        a = cinder_helper.VolumeSnapshot.from_openstacksdk(snap)
        b = cinder_helper.VolumeSnapshot.from_openstacksdk(snap)
        self.assertEqual(a, b)

    def test_inequality(self):
        snap1 = self.create_openstacksdk_volume_snapshot(volume_id='vol-1')
        snap2 = self.create_openstacksdk_volume_snapshot(volume_id='vol-2')
        a = cinder_helper.VolumeSnapshot.from_openstacksdk(snap1)
        b = cinder_helper.VolumeSnapshot.from_openstacksdk(snap2)
        self.assertNotEqual(a, b)


class TestCinderHelperConfigOverrides(base.TestCase):
    """Test suite for the CinderHelper config override functionality.

    Tests the deprecated config migration from the [cinder_client] to
    the [cinder] group.
    """

    def setUp(self):
        super().setUp()
        self.useFixture(
            fixtures.MockPatch("watcher.common.clients.get_sdk_connection")
        )

    def test_endpoint_type_override_public_url(self):
        """Test endpoint_type publicURL is converted to public."""
        self.flags(endpoint_type='publicURL', group='cinder_client')

        cinder_helper.CinderHelper()

        self.assertEqual(['public'], CONF.cinder.valid_interfaces)

    def test_endpoint_type_override_internal_url(self):
        """Test endpoint_type internalURL is converted to internal."""
        self.flags(endpoint_type='internalURL', group='cinder_client')

        cinder_helper.CinderHelper()

        self.assertEqual(['internal'], CONF.cinder.valid_interfaces)

    def test_endpoint_type_override_admin_url(self):
        """Test endpoint_type adminURL is converted to admin."""
        self.flags(endpoint_type='adminURL', group='cinder_client')

        cinder_helper.CinderHelper()

        self.assertEqual(['admin'], CONF.cinder.valid_interfaces)

    def test_endpoint_type_override_without_url_suffix(self):
        """Test endpoint_type without URL suffix is preserved."""
        self.flags(endpoint_type='public', group='cinder_client')

        cinder_helper.CinderHelper()

        self.assertEqual(['public'], CONF.cinder.valid_interfaces)

    def test_endpoint_type_override_internal_without_suffix(self):
        """Test endpoint_type internal without suffix is preserved."""
        self.flags(endpoint_type='internal', group='cinder_client')

        cinder_helper.CinderHelper()

        self.assertEqual(['internal'], CONF.cinder.valid_interfaces)

    def test_endpoint_type_override_admin_without_suffix(self):
        """Test endpoint_type admin without suffix is preserved."""
        self.flags(endpoint_type='admin', group='cinder_client')

        cinder_helper.CinderHelper()

        self.assertEqual(['admin'], CONF.cinder.valid_interfaces)
