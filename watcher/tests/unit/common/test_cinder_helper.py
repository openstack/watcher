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

from http import HTTPStatus
from unittest import mock

from cinderclient import exceptions as cinder_exception

from watcher.common import cinder_helper
from watcher.common import clients
from watcher.common import exception
from watcher.common import utils
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils


@mock.patch.object(clients.OpenStackClients, 'cinder')
class TestCinderHelper(test_utils.CinderResourcesMixin, base.TestCase):
    def test_get_storage_node_list(self, mock_cinder):
        node1 = self.create_cinder_storage_service()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        cinder_util.get_storage_node_list()
        cinder_util.cinder.services.list.assert_called_once_with(
            binary='cinder-volume'
        )

    def test_get_storage_node_by_name_success(self, mock_cinder):
        node1 = self.create_cinder_storage_service()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        node = cinder_util.get_storage_node_by_name('host@backend')

        self.assertEqual(node.host, 'host@backend')

    def test_get_storage_node_by_name_failure(self, mock_cinder):
        node1 = self.create_cinder_storage_service()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        self.assertRaisesRegex(
            exception.StorageNodeNotFound,
            "The storage node failure could not be found",
            cinder_util.get_storage_node_by_name,
            'failure',
        )

    def test_get_storage_pool_list(self, mock_cinder):
        pool = self.create_cinder_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.pools.list.return_value = [pool]
        cinder_util.get_storage_pool_list()
        cinder_util.cinder.pools.list.assert_called_once_with(detailed=True)

    def test_get_storage_pool_by_name_success(self, mock_cinder):
        pool1 = self.create_cinder_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.pools.list.return_value = [pool1]
        pool = cinder_util.get_storage_pool_by_name('host@backend#pool')

        self.assertEqual(pool.name, 'host@backend#pool')

    def test_get_storage_pool_by_name_failure(self, mock_cinder):
        pool1 = self.create_cinder_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [pool1]
        self.assertRaisesRegex(
            exception.PoolNotFound,
            "The pool failure could not be found",
            cinder_util.get_storage_pool_by_name,
            'failure',
        )

    def test_get_volume_type_list(self, mock_cinder):
        volume_type1 = self.create_cinder_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        cinder_util.get_volume_type_list()
        cinder_util.cinder.volume_types.list.assert_called_once_with()

    def test_get_volume_type_by_backendname_with_backend_exist(
        self, mock_cinder
    ):
        volume_type1 = self.create_cinder_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'backend'
        )

        self.assertEqual(volume_type_name[0], volume_type1.name)

    def test_get_volume_type_by_backendname_with_no_backend_exist(
        self, mock_cinder
    ):
        volume_type1 = self.create_cinder_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'nobackend'
        )

        self.assertEqual([], volume_type_name)

    def test_get_volume_type_name_by_id_found(self, mock_cinder):
        volume_type1 = self.create_cinder_volume_type(
            id='abc-123', name='my_type'
        )
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.get.return_value = volume_type1
        result = cinder_util.get_volume_type_name_by_id('abc-123')
        self.assertEqual('my_type', result)

    def test_get_volume_type_name_by_id_not_found(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.get.side_effect = (
            cinder_exception.NotFound(404)
        )
        self.assertRaises(
            exception.VolumeTypeNotFound,
            cinder_util.get_volume_type_name_by_id,
            'unknown-id',
        )

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_pool_by_name')
    def test_migrate_success(self, mock_get_pool, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume(
            os_vol_host_attr_host='source_node', migration_status='success'
        )
        cinder_util.cinder.volumes.get.return_value = volume

        volume_type = self.create_cinder_volume_type()
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        mock_pool = self.create_cinder_pool()
        mock_get_pool.return_value = mock_pool

        result = cinder_util.migrate(volume, 'host@backend#pool')
        mock_get_pool.assert_called_once_with('host@backend#pool')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_pool_by_name')
    def test_migrate_fail(self, mock_get_pool, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        mock_pool = self.create_cinder_pool()
        mock_get_pool.return_value = mock_pool

        volume_type = self.create_cinder_volume_type(
            name='notbackend',
            extra_specs={'volume_backend_name': 'diff_backend'},
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]

        self.assertRaisesRegex(
            exception.Invalid,
            "Volume type 'fake_type' is not compatible with destination "
            "pool 'host@backend#pool'",
            cinder_util.migrate,
            volume,
            'host@backend#pool',
        )

        volume = self.create_cinder_volume(
            migration_status='error', os_vol_host_attr_host='source_node'
        )
        cinder_util.cinder.volumes.get.return_value = volume

        # check that a volume type without any volume_backend_name passes the
        # volume type check and proceeds to the migration
        volume_type = self.create_cinder_volume_type(extra_specs={})
        cinder_util.cinder.volume_types.list.return_value = [volume_type]

        result = cinder_util.migrate(volume, 'host@backend#pool')
        mock_get_pool.assert_called_with('host@backend#pool')
        cinder_util.cinder.volumes.migrate_volume.assert_called_with(
            volume.id, 'host@backend#pool', False, True
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    def test_retype_success(self, mock_get_volume, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        volume.host = 'source_node'
        volume.migration_status = 'success'

        def side_effect(volume, status, volume_type):
            volume_info = volume.to_dict()
            volume_info["status"] = status
            volume_info["volume_type"] = volume_type
            return cinder_helper.Volume.from_cinderclient(
                self.create_cinder_volume(**volume_info)
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'in-use', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'notfake_type'),
            side_effect(volume, 'in-use', 'notfake_type'),
        ]
        cinder_util.cinder.volumes.get.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_retype_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        # dest_type is the actual one
        volume = self.create_cinder_volume(
            host='source_node', migration_status='success'
        )
        cinder_util.cinder.volumes.get.return_value = volume

        self.assertRaisesRegex(
            exception.Invalid,
            "Volume type must be different for retyping",
            cinder_util.retype,
            volume,
            'fake_type',
        )

        # type is not the expected one
        volume = self.create_cinder_volume()
        cinder_util.cinder.volumes.get.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertFalse(result)

        # type is correct but status is error
        volume = self.create_cinder_volume(status='error')
        cinder_util.cinder.volumes.get.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_can_get_volume_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        cinder_util.get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util._can_get_volume(volume.id)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_can_get_volume_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        cinder_util.get_volume = mock.MagicMock()
        cinder_util.get_volume.side_effect = (
            exception.StorageResourceNotFound()
        )
        result = cinder_util._can_get_volume(volume.id)
        self.assertFalse(result)

        cinder_util.get_volume = mock.MagicMock(return_value=None)
        self.assertFalse(result)

    def test_can_get_volume_not_found_via_decorator(self, mock_cinder):
        """_can_get_volume returns False through the decorator path."""
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volumes.get.side_effect = cinder_exception.NotFound(
            HTTPStatus.NOT_FOUND
        )
        cinder_util.cinder.volumes.find.side_effect = (
            cinder_exception.NotFound(HTTPStatus.NOT_FOUND)
        )
        result = cinder_util._can_get_volume('missing-vol')
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_get_volume_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        result = cinder_util.get_volume(volume)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_get_volume_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        side_effect = cinder_exception.NotFound(HTTPStatus.NOT_FOUND)
        cinder_util.cinder.volumes.get.side_effect = side_effect
        found = self.create_cinder_volume(name='found_by_name')
        cinder_util.cinder.volumes.find.return_value = found
        result = cinder_util.get_volume(volume)
        self.assertEqual(result.name, 'found_by_name')

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_volume_deleted_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util._can_get_volume = mock.MagicMock(return_value=None)
        result = cinder_util.check_volume_deleted(
            volume, retry=2, retry_interval=1
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_volume_deleted_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util._can_get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_volume_deleted(
            volume, retry=2, retry_interval=1
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_migrated_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume()
        volume.migration_status = 'success'
        volume.host = 'host@backend#pool'
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_migrated(volume)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_migrated_fail(self, mock_cinder):
        def side_effect(volume):
            if isinstance(volume, str):
                volume = self.create_cinder_volume()
                volume.migration_status = 'error'
                volume.host = 'source_node'
            elif volume.id is None:
                volume.migration_status = 'fake_status'
                volume.id = utils.generate_uuid()
            return volume

        cinder_util = cinder_helper.CinderHelper()

        # verify that the method check_migrated will return False when the
        # status of migration_status is error.
        volume = self.create_cinder_volume()
        volume.migration_status = 'error'
        volume.host = 'source_node'
        cinder_util.cinder.volumes.get.return_value = volume
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

        # verify that the method check_migrated will return False when the
        # status of migration_status is in other cases.
        volume = self.create_cinder_volume()
        volume.migration_status = 'success'
        volume.host = 'source_node'
        volume.id = None
        cinder_util.get_volume = mock.MagicMock()
        cinder_util.get_volume.side_effect = side_effect
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

        # verify that the method check_migrated will return False when the
        # return_value of method check_volume_deleted is False.
        volume = self.create_cinder_volume()
        volume.migration_status = 'success'
        volume.host = 'source_node'
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=False)
        cinder_util.get_deleting_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.LOG, 'debug')
    def test_check_retyped_success_immediate(
        self, mock_log_debug, mock_cinder
    ):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.create_cinder_volume(
            status='in-use', volume_type='dest_type'
        )
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_retyped(volume, 'dest_type')
        self.assertNotIn(
            mock.call('Waiting the retype of %s', volume),
            mock_log_debug.mock_calls,
        )
        mock_log_debug.assert_called_with(
            "Volume retype succeeded : volume %(volume)s has now type "
            "'%(type)s'.",
            {'volume': volume.id, 'type': 'dest_type'},
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    def test_check_retyped_success_retries(
        self, mock_log_debug, mock_get_volume, mock_cinder
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_cinder_volume(status='in-use')

        def side_effect(volume, status, volume_type):
            volume_info = volume.to_dict()
            volume_info["status"] = status
            volume_info["volume_type"] = volume_type
            return cinder_helper.Volume.from_cinderclient(
                self.create_cinder_volume(**volume_info)
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'dest_type'),
        ]

        wrap_vol = cinder_helper.Volume.from_cinderclient(volume)
        cinder_util.cinder.volumes.get.return_value = wrap_vol
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_retyped(volume, 'dest_type')
        self.assertEqual(mock_get_volume.call_count, 3)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_debug.assert_called_with(
            "Volume retype succeeded : volume %(volume)s has now type "
            "'%(type)s'.",
            {'volume': volume.id, 'type': 'dest_type'},
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    def test_check_retyped_success_retries_migration(
        self, mock_log_debug, mock_get_volume, mock_cinder
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_cinder_volume(
            status='in-use',
            migration_status='success',
            os_vol_host_attr_host='source_node',
        )

        def side_effect(volume, status, volume_type):
            volume_info = volume.to_dict()
            volume_info["status"] = status
            volume_info["volume_type"] = volume_type
            return cinder_helper.Volume.from_cinderclient(
                self.create_cinder_volume(**volume_info)
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'dest_type'),
        ]

        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        cinder_util.get_deleting_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_retyped(volume, 'dest_type')
        self.assertEqual(mock_get_volume.call_count, 3)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_debug.assert_called_with(
            "Volume retype succeeded : volume %(volume)s has now type "
            "'%(type)s'.",
            {'volume': volume.id, 'type': 'dest_type'},
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    @mock.patch.object(cinder_helper.LOG, 'error')
    def test_check_retyped_failed_available(
        self, mock_log_error, mock_log_debug, mock_get_volume, mock_cinder
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_cinder_volume(status='available')

        def side_effect(volume, status, volume_type):
            volume_info = volume.to_dict()
            volume_info["status"] = status
            volume_info["volume_type"] = volume_type
            return cinder_helper.Volume.from_cinderclient(
                self.create_cinder_volume(**volume_info)
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'available', 'fake_type'),
        ]

        cinder_util.cinder.volumes.get.return_value = volume
        result = cinder_util.check_retyped(
            volume, 'dest_type', retry_interval=1
        )
        self.assertEqual(mock_get_volume.call_count, 3)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_error.assert_called_with(
            "Volume retype failed : volume %(volume)s has now type "
            "'%(type)s' and status %(status)s",
            {'volume': volume.id, 'type': 'fake_type', 'status': 'available'},
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    @mock.patch.object(cinder_helper.LOG, 'debug')
    @mock.patch.object(cinder_helper.LOG, 'error')
    def test_check_retyped_failed_inuse(
        self, mock_log_error, mock_log_debug, mock_get_volume, mock_cinder
    ):
        cinder_util = cinder_helper.CinderHelper()
        volume = self.create_cinder_volume(
            status='in-use', migration_status='error'
        )

        def side_effect(volume, status, volume_type):
            volume_info = volume.to_dict()
            volume_info["status"] = status
            volume_info["volume_type"] = volume_type
            return cinder_helper.Volume.from_cinderclient(
                self.create_cinder_volume(**volume_info)
            )

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'fake_type'),
        ]

        cinder_util.cinder.volumes.get.return_value = volume
        result = cinder_util.check_retyped(
            volume, 'dest_type', retry_interval=1
        )
        self.assertEqual(mock_get_volume.call_count, 4)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume.id)
        mock_log_error.assert_any_call(
            "Volume retype failed : volume %(volume)s has now type "
            "'%(type)s' and status %(status)s",
            {'volume': volume.id, 'type': 'fake_type', 'status': 'in-use'},
        )
        mock_log_error.assert_called_with(
            "Volume migration error on volume %(volume)s.",
            {'volume': volume.id},
        )
        self.assertFalse(result)

    def test_get_volume_types_for_pool_matching_backend(self, mock_cinder):
        """Test matching backend and no extra_specs are selected."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_cinderclient(
            self.create_cinder_pool(
                name='host@backend#pool',
                capabilities={'volume_backend_name': 'backend'},
            )
        )
        volume_type1 = self.create_cinder_volume_type(
            name='type_matching',
            extra_specs={'volume_backend_name': 'backend'},
        )
        volume_type2 = self.create_cinder_volume_type(
            name='type_no_specs', extra_specs={}
        )
        cinder_util.cinder.volume_types.list.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(sorted(result), ['type_matching', 'type_no_specs'])

    def test_get_volume_types_for_pool_different_backend(self, mock_cinder):
        """Test different backend is excluded, no specs is included."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_cinderclient(
            self.create_cinder_pool(
                name='host@backend#pool',
                capabilities={'volume_backend_name': 'backend'},
            )
        )
        volume_type1 = self.create_cinder_volume_type(
            name='type_no_specs', extra_specs={}
        )
        volume_type2 = self.create_cinder_volume_type(
            name='type_different_backend',
            extra_specs={'volume_backend_name': 'different_backend'},
        )
        cinder_util.cinder.volume_types.list.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_no_specs'])

    def test_get_volume_types_for_pool_matching_capability(self, mock_cinder):
        """Test volume type with matching capability is selected."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_cinderclient(
            self.create_cinder_pool(
                name='host@backend#pool', capabilities={'disk_speed': 'fast'}
            )
        )
        volume_type = self.create_cinder_volume_type(
            name='type_fast_disk', extra_specs={'disk_speed': 'fast'}
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_fast_disk'])

    def test_get_volume_types_for_pool_mismatched_capability(
        self, mock_cinder
    ):
        """Test volume type with different capability value excluded."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_cinderclient(
            self.create_cinder_pool(
                name='host@backend#pool', capabilities={'disk_speed': 'fast'}
            )
        )
        volume_type = self.create_cinder_volume_type(
            name='type_slow_disk', extra_specs={'disk_speed': 'slow'}
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual([], result)

    def test_get_volume_types_for_pool_no_capabilities(self, mock_cinder):
        """Test pool with no capabilities selects no-specs types."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_cinderclient(
            self.create_cinder_pool(name='host@backend#pool', capabilities={})
        )
        volume_type1 = self.create_cinder_volume_type(
            name='type_no_specs', extra_specs={}
        )
        volume_type2 = self.create_cinder_volume_type(
            name='type_with_specs',
            extra_specs={'volume_backend_name': 'backend'},
        )
        cinder_util.cinder.volume_types.list.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_no_specs', 'type_with_specs'])

    def test_get_volume_types_for_pool_requirements_not_in_caps(
        self, mock_cinder
    ):
        """Test volume type with requirements not in pool capabilities."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_cinderclient(
            self.create_cinder_pool(
                name='host@backend#pool',
                capabilities={'volume_backend_name': 'backend'},
            )
        )
        volume_type = self.create_cinder_volume_type(
            name='type_extra_reqs',
            extra_specs={
                'volume_backend_name': 'backend',
                'disk_speed': 'fast',
            },
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual(result, ['type_extra_reqs'])

    def test_get_volume_types_for_pool_multiple_specs_partial_match(
        self, mock_cinder
    ):
        """Test volume type with multiple extra_specs partial match."""
        cinder_util = cinder_helper.CinderHelper()
        pool = cinder_helper.StoragePool.from_cinderclient(
            self.create_cinder_pool(
                name='host@backend#pool',
                capabilities={
                    'volume_backend_name': 'backend',
                    'disk_speed': 'fast',
                    'compression': 'enabled',
                },
            )
        )
        volume_type = self.create_cinder_volume_type(
            name='type_partial',
            extra_specs={
                'volume_backend_name': 'backend',
                'disk_speed': 'slow',
                'compression': 'enabled',
            },
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool)
        self.assertEqual([], result)


@mock.patch.object(clients.OpenStackClients, 'cinder')
class TestHandleCinderError(test_utils.CinderResourcesMixin, base.TestCase):
    """Tests for the handle_cinder_error decorator."""

    def test_not_found_raises_storage_resource_not_found(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volumes.get.side_effect = cinder_exception.NotFound(
            HTTPStatus.NOT_FOUND
        )
        cinder_util.cinder.volumes.find.side_effect = (
            cinder_exception.NotFound(HTTPStatus.NOT_FOUND)
        )
        self.assertRaises(
            exception.StorageResourceNotFound,
            cinder_util.get_volume,
            'missing-vol',
        )

    def test_client_exception_raises_cinder_client_error(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volumes.list.side_effect = (
            cinder_exception.ClientException(HTTPStatus.BAD_REQUEST)
        )
        self.assertRaises(
            exception.CinderClientError, cinder_util.get_volume_list
        )

    def test_not_found_on_list_raises_storage_resource_not_found(
        self, mock_cinder
    ):
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.pools.list.side_effect = cinder_exception.NotFound(
            HTTPStatus.NOT_FOUND
        )
        self.assertRaises(
            exception.StorageResourceNotFound,
            cinder_util.get_storage_pool_list,
        )


class TestStorageService(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the StorageService dataclass wrapper."""

    def test_from_cinderclient(self):
        svc = self.create_cinder_storage_service()
        result = cinder_helper.StorageService.from_cinderclient(svc)
        self.assertEqual('host@backend', result.host)
        self.assertEqual('nova', result.zone)
        self.assertEqual('up', result.state)
        self.assertEqual('enabled', result.status)

    def test_from_cinderclient_custom_values(self):
        svc = self.create_cinder_storage_service(
            host='node1@lvm', zone='az1', state='down', status='disabled'
        )
        result = cinder_helper.StorageService.from_cinderclient(svc)
        self.assertEqual('node1@lvm', result.host)
        self.assertEqual('az1', result.zone)
        self.assertEqual('down', result.state)
        self.assertEqual('disabled', result.status)

    def test_frozen(self):
        svc = self.create_cinder_storage_service()
        result = cinder_helper.StorageService.from_cinderclient(svc)
        self.assertRaises(dc.FrozenInstanceError, setattr, result, 'host', 'x')

    def test_equality(self):
        svc = self.create_cinder_storage_service()
        a = cinder_helper.StorageService.from_cinderclient(svc)
        b = cinder_helper.StorageService.from_cinderclient(svc)
        self.assertEqual(a, b)

    def test_inequality(self):
        svc1 = self.create_cinder_storage_service(host='host1')
        svc2 = self.create_cinder_storage_service(host='host2')
        a = cinder_helper.StorageService.from_cinderclient(svc1)
        b = cinder_helper.StorageService.from_cinderclient(svc2)
        self.assertNotEqual(a, b)


class TestStoragePool(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the StoragePool dataclass wrapper."""

    def test_from_cinderclient_defaults(self):
        pool = self.create_cinder_pool()
        result = cinder_helper.StoragePool.from_cinderclient(pool)
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

    def test_from_cinderclient_custom_values(self):
        pool = self.create_cinder_pool(
            name='node1@ceph#ssd_pool',
            total_capacity_gb=500.0,
            free_capacity_gb=200.0,
            provisioned_capacity_gb=300.0,
            allocated_capacity_gb=250.0,
            total_volumes=42,
            max_over_subscription_ratio=2.0,
            volume_backend_name='ceph',
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertEqual('node1@ceph#ssd_pool', result.name)
        self.assertEqual('ssd_pool', result.pool_name)
        self.assertEqual(42, result.total_volumes)
        self.assertEqual(500.0, result.total_capacity_gb)
        self.assertEqual(200.0, result.free_capacity_gb)
        self.assertEqual(300.0, result.provisioned_capacity_gb)
        self.assertEqual(250.0, result.allocated_capacity_gb)
        self.assertEqual(2.0, result.max_over_subscription_ratio)
        self.assertEqual('ceph', result.volume_backend_name)

    def test_from_cinderclient_unknown_capacities(self):
        """Capacity values of 'unknown' should become None."""
        pool = self.create_cinder_pool(
            capabilities={
                'total_capacity_gb': 'unknown',
                'free_capacity_gb': 'unknown',
                'provisioned_capacity_gb': 'unknown',
                'allocated_capacity_gb': 'unknown',
            }
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertIsNone(result.total_capacity_gb)
        self.assertIsNone(result.free_capacity_gb)
        self.assertIsNone(result.provisioned_capacity_gb)
        self.assertIsNone(result.allocated_capacity_gb)

    def test_from_cinderclient_none_capacities(self):
        """Capacity values of None should remain None."""
        pool = self.create_cinder_pool(
            capabilities={
                'total_capacity_gb': None,
                'free_capacity_gb': None,
                'provisioned_capacity_gb': None,
                'allocated_capacity_gb': None,
            }
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertIsNone(result.total_capacity_gb)
        self.assertIsNone(result.free_capacity_gb)
        self.assertIsNone(result.provisioned_capacity_gb)
        self.assertIsNone(result.allocated_capacity_gb)

    def test_from_cinderclient_mixed_capacities(self):
        """Mix of numeric, 'unknown', and None capacity values."""
        pool = self.create_cinder_pool(
            capabilities={
                'total_capacity_gb': 100.0,
                'free_capacity_gb': 'unknown',
                'provisioned_capacity_gb': None,
                'allocated_capacity_gb': 25,
            }
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertEqual(100.0, result.total_capacity_gb)
        self.assertIsNone(result.free_capacity_gb)
        self.assertIsNone(result.provisioned_capacity_gb)
        self.assertEqual(25.0, result.allocated_capacity_gb)

    def test_from_cinderclient_integer_capacities_become_float(self):
        """Integer capacity values should be converted to float."""
        pool = self.create_cinder_pool(
            total_capacity_gb=100,
            free_capacity_gb=50,
            provisioned_capacity_gb=50,
            allocated_capacity_gb=50,
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertIsInstance(result.total_capacity_gb, float)
        self.assertIsInstance(result.free_capacity_gb, float)
        self.assertIsInstance(result.provisioned_capacity_gb, float)
        self.assertIsInstance(result.allocated_capacity_gb, float)

    def test_from_cinderclient_capabilities_preserved(self):
        """Extra capabilities beyond standard fields are preserved."""
        pool = self.create_cinder_pool(
            capabilities={
                'total_capacity_gb': 100.0,
                'free_capacity_gb': 50.0,
                'provisioned_capacity_gb': 50.0,
                'allocated_capacity_gb': 50.0,
                'volume_backend_name': 'backend',
                'disk_speed': 'fast',
            }
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertEqual('fast', result.capabilities.get('disk_speed'))

    def test_from_cinderclient_only_nonstandard_capabilities(self):
        """Capabilities with only non-standard fields."""
        pool = self.create_cinder_pool(
            capabilities={'custom_key': 'custom_value'}
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertEqual(result.capabilities, {'custom_key': 'custom_value'})
        self.assertAlmostEqual(100.0, result.total_capacity_gb)
        self.assertAlmostEqual(50.0, result.free_capacity_gb)
        self.assertAlmostEqual(50.0, result.provisioned_capacity_gb)
        self.assertAlmostEqual(50.0, result.allocated_capacity_gb)

    def test_not_frozen_allows_mutation(self):
        """StoragePool is not frozen, allowing field mutation."""
        pool = self.create_cinder_pool()
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        result.free_capacity_gb = 25.0
        self.assertEqual(25.0, result.free_capacity_gb)

    def test_from_cinderclient_no_pool_name(self):
        """Pool without '#' in name should have pool_name from dict."""
        pool = self.create_cinder_pool(name='host@backend', pool_name='mypool')
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertEqual('host@backend', result.name)
        self.assertEqual('mypool', result.pool_name)

    def test_from_cinderclient_missing_optional_fields(self):
        """Missing optional fields use defaults."""
        pool = self.create_cinder_pool(
            capabilities={
                'total_capacity_gb': 100.0,
                'free_capacity_gb': 50.0,
                'provisioned_capacity_gb': 50.0,
                'allocated_capacity_gb': 50.0,
            }
        )
        result = cinder_helper.StoragePool.from_cinderclient(pool)
        self.assertIsNotNone(result.name)


class TestVolume(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the Volume dataclass wrapper."""

    def test_from_cinderclient_defaults(self):
        vol = self.create_cinder_volume()
        result = cinder_helper.Volume.from_cinderclient(vol)
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
        self.assertIsNone(result.name_id)
        self.assertIsNone(result.snapshot_id)

    def test_from_cinderclient_custom_values(self):
        vol = self.create_cinder_volume(
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
            name_id='name-id-123',
            snapshot_id='snap-456',
            tenant_id='tenant-789',
        )
        result = cinder_helper.Volume.from_cinderclient(vol)
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
        self.assertEqual('name-id-123', result.name_id)
        self.assertEqual('snap-456', result.snapshot_id)
        self.assertEqual('tenant-789', result.tenant_id)

    def test_from_cinderclient_hyphenated_attrs(self):
        """Hyphenated cinderclient attrs are mapped correctly."""
        vol = self.create_cinder_volume(
            host='host@backend#pool',
            tenant_id='project-abc',
            name_id='name-id-xyz',
        )
        result = cinder_helper.Volume.from_cinderclient(vol)
        self.assertEqual('host@backend#pool', result.host)
        self.assertEqual('project-abc', result.tenant_id)
        self.assertEqual('name-id-xyz', result.name_id)

    def test_frozen(self):
        vol = self.create_cinder_volume()
        result = cinder_helper.Volume.from_cinderclient(vol)
        self.assertRaises(
            dc.FrozenInstanceError, setattr, result, 'status', 'x'
        )

    def test_equality(self):
        vol = self.create_cinder_volume()
        a = cinder_helper.Volume.from_cinderclient(vol)
        b = cinder_helper.Volume.from_cinderclient(vol)
        self.assertEqual(a, b)

    def test_with_none_optional_fields(self):
        """All optional fields can be None."""
        vol = self.create_cinder_volume(
            host=None,
            migration_status=None,
            name_id=None,
            snapshot_id=None,
            tenant_id=None,
        )
        result = cinder_helper.Volume.from_cinderclient(vol)
        self.assertIsNone(result.host)
        self.assertIsNone(result.migration_status)
        self.assertIsNone(result.name_id)
        self.assertIsNone(result.snapshot_id)
        self.assertIsNone(result.tenant_id)

    def test_with_multiple_attachments(self):
        attachments = [
            {'server_id': 'srv-1', 'device': '/dev/vdb'},
            {'server_id': 'srv-2', 'device': '/dev/vdc'},
        ]
        vol = self.create_cinder_volume(attachments=attachments)
        result = cinder_helper.Volume.from_cinderclient(vol)
        self.assertEqual(2, len(result.attachments))
        self.assertEqual('srv-1', result.attachments[0]['server_id'])
        self.assertEqual('srv-2', result.attachments[1]['server_id'])

    def test_with_metadata(self):
        metadata = {'env': 'prod', 'app': 'web'}
        vol = self.create_cinder_volume(metadata=metadata)
        result = cinder_helper.Volume.from_cinderclient(vol)
        self.assertEqual('prod', result.metadata['env'])
        self.assertEqual('web', result.metadata['app'])


class TestVolumeType(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the VolumeType dataclass wrapper."""

    def test_from_cinderclient_defaults(self):
        vt = self.create_cinder_volume_type()
        result = cinder_helper.VolumeType.from_cinderclient(vt)
        self.assertEqual('a1b2c3d4-e5f6-7890-abcd-ef1234567890', result.id)
        self.assertEqual('fake_type', result.name)
        self.assertEqual(
            {'volume_backend_name': 'backend'}, result.extra_specs
        )

    def test_from_cinderclient_custom_values(self):
        vt = self.create_cinder_volume_type(
            id='b2c3d4e5-f6a7-8901-bcde-f12345678901',
            name='ssd-type',
            extra_specs={'volume_backend_name': 'ceph', 'disk_speed': 'fast'},
        )
        result = cinder_helper.VolumeType.from_cinderclient(vt)
        self.assertEqual('b2c3d4e5-f6a7-8901-bcde-f12345678901', result.id)
        self.assertEqual('ssd-type', result.name)
        self.assertEqual('ceph', result.extra_specs['volume_backend_name'])
        self.assertEqual('fast', result.extra_specs['disk_speed'])

    def test_from_cinderclient_empty_extra_specs(self):
        vt = self.create_cinder_volume_type(name='generic', extra_specs={})
        result = cinder_helper.VolumeType.from_cinderclient(vt)
        self.assertEqual('generic', result.name)
        self.assertEqual({}, result.extra_specs)

    def test_frozen(self):
        vt = self.create_cinder_volume_type()
        result = cinder_helper.VolumeType.from_cinderclient(vt)
        self.assertRaises(dc.FrozenInstanceError, setattr, result, 'name', 'x')

    def test_equality(self):
        vt = self.create_cinder_volume_type()
        a = cinder_helper.VolumeType.from_cinderclient(vt)
        b = cinder_helper.VolumeType.from_cinderclient(vt)
        self.assertEqual(a, b)


class TestVolumeSnapshot(test_utils.CinderResourcesMixin, base.BaseTestCase):
    """Tests for the VolumeSnapshot dataclass wrapper."""

    def test_from_cinderclient_defaults(self):
        snap = self.create_cinder_volume_snapshot()
        result = cinder_helper.VolumeSnapshot.from_cinderclient(snap)
        self.assertEqual(
            'd010ef1f-dc19-4982-9383-087498bfde03', result.volume_id
        )

    def test_from_cinderclient_custom_values(self):
        snap = self.create_cinder_volume_snapshot(volume_id='custom-vol-id')
        result = cinder_helper.VolumeSnapshot.from_cinderclient(snap)
        self.assertEqual('custom-vol-id', result.volume_id)

    def test_frozen(self):
        snap = self.create_cinder_volume_snapshot()
        result = cinder_helper.VolumeSnapshot.from_cinderclient(snap)
        self.assertRaises(
            dc.FrozenInstanceError, setattr, result, 'volume_id', 'x'
        )

    def test_equality(self):
        snap = self.create_cinder_volume_snapshot()
        a = cinder_helper.VolumeSnapshot.from_cinderclient(snap)
        b = cinder_helper.VolumeSnapshot.from_cinderclient(snap)
        self.assertEqual(a, b)

    def test_inequality(self):
        snap1 = self.create_cinder_volume_snapshot(volume_id='vol-1')
        snap2 = self.create_cinder_volume_snapshot(volume_id='vol-2')
        a = cinder_helper.VolumeSnapshot.from_cinderclient(snap1)
        b = cinder_helper.VolumeSnapshot.from_cinderclient(snap2)
        self.assertNotEqual(a, b)
