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

import copy
import time

from http import HTTPStatus
from unittest import mock

from cinderclient import exceptions as cinder_exception
from cinderclient.v3.pools import Pool as CinderPool
from cinderclient.v3.volume_types import VolumeType as CinderVolType
from cinderclient.v3.volumes import Volume as CinderVolume

from watcher.common import cinder_helper
from watcher.common import clients
from watcher.common import exception
from watcher.common import utils
from watcher.tests.unit import base


@mock.patch.object(clients.OpenStackClients, 'cinder')
class TestCinderHelper(base.TestCase):
    @staticmethod
    def fake_storage_node(**kwargs):
        node = mock.MagicMock()
        node.binary = kwargs.get('binary', 'cinder-volume')
        node.host = kwargs.get('name', 'host@backend')

        return node

    def test_get_storage_node_list(self, mock_cinder):
        node1 = self.fake_storage_node()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        cinder_util.get_storage_node_list()
        cinder_util.cinder.services.list.assert_called_once_with(
            binary='cinder-volume'
        )

    def test_get_storage_node_by_name_success(self, mock_cinder):
        node1 = self.fake_storage_node()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        node = cinder_util.get_storage_node_by_name('host@backend')

        self.assertEqual(node, node1)

    def test_get_storage_node_by_name_failure(self, mock_cinder):
        node1 = self.fake_storage_node()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [node1]
        self.assertRaisesRegex(
            exception.StorageNodeNotFound,
            "The storage node failure could not be found",
            cinder_util.get_storage_node_by_name,
            'failure',
        )

    @staticmethod
    def fake_pool(**kwargs):
        pool = mock.MagicMock(spec=CinderPool)
        pool.name = kwargs.get('name', 'host@backend#pool')
        host_backend = pool.name.split('#')[0]
        default_capabilities = {
            'volume_backend_name': host_backend.split('@')[1]
        }
        pool.capabilities = kwargs.get('capabilities', default_capabilities)

        def _to_dict():
            return {'name': pool.name, 'capabilities': pool.capabilities}

        pool.to_dict = _to_dict

        return pool

    def test_get_storage_pool_list(self, mock_cinder):
        pool = self.fake_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.pools.list.return_value = [pool]
        cinder_util.get_storage_pool_list()
        cinder_util.cinder.pools.list.assert_called_once_with(detailed=True)

    def test_get_storage_pool_by_name_success(self, mock_cinder):
        pool1 = self.fake_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.pools.list.return_value = [pool1]
        pool = cinder_util.get_storage_pool_by_name('host@backend#pool')

        self.assertEqual(pool, pool1)

    def test_get_storage_pool_by_name_failure(self, mock_cinder):
        pool1 = self.fake_pool()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.services.list.return_value = [pool1]
        self.assertRaisesRegex(
            exception.PoolNotFound,
            "The pool failure could not be found",
            cinder_util.get_storage_pool_by_name,
            'failure',
        )

    @staticmethod
    def fake_volume_type(**kwargs):
        volume_type = mock.MagicMock(spec=CinderVolType)
        volume_type.name = kwargs.get('name', 'fake_type')
        extra_specs = {'volume_backend_name': 'backend'}
        volume_type.extra_specs = kwargs.get('extra_specs', extra_specs)
        return volume_type

    def test_get_volume_type_list(self, mock_cinder):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        cinder_util.get_volume_type_list()
        cinder_util.cinder.volume_types.list.assert_called_once_with()

    def test_get_volume_type_by_backendname_with_backend_exist(
        self, mock_cinder
    ):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'backend'
        )

        self.assertEqual(volume_type_name[0], volume_type1.name)

    def test_get_volume_type_by_backendname_with_no_backend_exist(
        self, mock_cinder
    ):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'nobackend'
        )

        self.assertEqual([], volume_type_name)

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock(spec=CinderVolume)
        volume.id = kwargs.get('id', '45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba')
        volume.name = kwargs.get('name', 'fakename')
        volume.size = kwargs.get('size', '1')
        volume.status = kwargs.get('status', 'available')
        volume.snapshot_id = kwargs.get('snapshot_id', None)
        volume.availability_zone = kwargs.get('availability_zone', 'nova')
        volume.volume_type = kwargs.get('volume_type', 'fake_type')
        volume.migration_status = kwargs.get('migration_status')
        setattr(
            volume,
            'os-vol-host-attr:host',
            kwargs.get('os_vol_host_attr_host'),
        )
        return volume

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_pool_by_name')
    def test_migrate_success(self, mock_get_pool, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume(
            os_vol_host_attr_host='source_node', migration_status='success'
        )
        cinder_util.cinder.volumes.get.return_value = volume

        volume_type = self.fake_volume_type()
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        mock_pool = self.fake_pool()
        mock_get_pool.return_value = mock_pool

        result = cinder_util.migrate(volume, 'host@backend#pool')
        mock_get_pool.assert_called_once_with('host@backend#pool')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_pool_by_name')
    def test_migrate_fail(self, mock_get_pool, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        mock_pool = self.fake_pool()
        mock_get_pool.return_value = mock_pool

        volume_type = self.fake_volume_type(
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

        volume = self.fake_volume(
            migration_status='error', os_vol_host_attr_host='source_node'
        )
        cinder_util.cinder.volumes.get.return_value = volume

        # check that a volume type without any volume_backend_name passes the
        # volume type check and proceeds to the migration
        volume_type = self.fake_volume_type(extra_specs={})
        cinder_util.cinder.volume_types.list.return_value = [volume_type]

        result = cinder_util.migrate(volume, 'host@backend#pool')
        mock_get_pool.assert_called_with('host@backend#pool')
        cinder_util.cinder.volumes.migrate_volume.assert_called_with(
            volume, 'host@backend#pool', False, True
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    @mock.patch.object(cinder_helper.CinderHelper, 'get_volume')
    def test_retype_success(self, mock_get_volume, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'migration_status', 'success')

        def side_effect(volume, status, volume_type):
            result_volume = copy.deepcopy(volume)
            result_volume.status = status
            result_volume.volume_type = volume_type
            return result_volume

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
        volume = self.fake_volume()
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'migration_status', 'success')
        cinder_util.cinder.volumes.get.return_value = volume

        self.assertRaisesRegex(
            exception.Invalid,
            "Volume type must be different for retyping",
            cinder_util.retype,
            volume,
            'fake_type',
        )

        # type is not the expected one
        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertFalse(result)

        # type is correct but status is error
        volume = self.fake_volume(status='error')
        cinder_util.cinder.volumes.get.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_create_volume_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.cinder.volumes.create.return_value = volume
        new_vloume = cinder_util.create_volume(
            cinder_util.cinder, volume, 'fake_type'
        )
        self.assertEqual(new_vloume, volume)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_create_volume_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        setattr(volume, 'status', 'fake_status')
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.cinder.volumes.create.return_value = volume

        self.assertRaisesRegex(
            Exception,
            "Failed to create volume",
            cinder_util.create_volume,
            cinder_util.cinder,
            volume,
            'fake_type',
            retry=2,
            retry_interval=1,
        )

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_delete_volume_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.cinder.volumes.create.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.delete_volume(volume)
        self.assertIsNone(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_delete_volume_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        setattr(volume, 'status', 'fake_status')
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.cinder.volumes.create.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=False)

        self.assertRaisesRegex(
            Exception,
            "Failed to delete volume",
            cinder_util.delete_volume,
            volume,
        )

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_can_get_volume_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util._can_get_volume(volume.id)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_can_get_volume_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.get_volume = mock.MagicMock()
        cinder_util.get_volume.side_effect = cinder_exception.NotFound(
            HTTPStatus.NOT_FOUND
        )
        result = cinder_util._can_get_volume(volume.id)
        self.assertFalse(result)

        cinder_util.get_volume = mock.MagicMock(return_value=None)
        self.assertRaises(Exception, cinder_util._can_get_volume, volume.id)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_has_snapshot_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        volume.snapshot_id = utils.generate_uuid()
        cinder_util.get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util._has_snapshot(volume)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_has_snapshot_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        volume.snapshot_id = None
        cinder_util.get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util._has_snapshot(volume)
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_get_volume_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        result = cinder_util.get_volume(volume)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_get_volume_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        side_effect = cinder_exception.NotFound(HTTPStatus.NOT_FOUND)
        cinder_util.cinder.volumes.get.side_effect = side_effect
        cinder_util.cinder.volumes.find.return_value = False
        result = cinder_util.get_volume(volume)
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_volume_deleted_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util._can_get_volume = mock.MagicMock(return_value=None)
        result = cinder_util.check_volume_deleted(
            volume, retry=2, retry_interval=1
        )
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_volume_deleted_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util._can_get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_volume_deleted(
            volume, retry=2, retry_interval=1
        )
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_migrated_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        setattr(volume, 'migration_status', 'success')
        setattr(volume, 'os-vol-host-attr:host', 'host@backend#pool')
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_migrated(volume)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_migrated_fail(self, mock_cinder):
        def side_effect(volume):
            if isinstance(volume, str):
                volume = self.fake_volume()
                setattr(volume, 'migration_status', 'error')
            elif volume.id is None:
                setattr(volume, 'migration_status', 'fake_status')
                setattr(volume, 'id', utils.generate_uuid())
            return volume

        cinder_util = cinder_helper.CinderHelper()

        # verify that the method check_migrated will return False when the
        # status of migration_status is error.
        volume = self.fake_volume()
        setattr(volume, 'migration_status', 'error')
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        cinder_util.cinder.volumes.get.return_value = volume
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

        # verify that the method check_migrated will return False when the
        # status of migration_status is in other cases.
        volume = self.fake_volume()
        setattr(volume, 'migration_status', 'success')
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'id', None)
        cinder_util.get_volume = mock.MagicMock()
        cinder_util.get_volume.side_effect = side_effect
        result = cinder_util.check_migrated(volume, retry_interval=1)
        self.assertFalse(result)

        # verify that the method check_migrated will return False when the
        # return_value of method check_volume_deleted is False.
        volume = self.fake_volume()
        setattr(volume, 'migration_status', 'success')
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
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

        volume = self.fake_volume(status='in-use', volume_type='dest_type')
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
        volume = self.fake_volume(status='in-use')

        def side_effect(volume, status, volume_type):
            result_volume = copy.deepcopy(volume)
            result_volume.status = status
            result_volume.volume_type = volume_type
            return result_volume

        mock_get_volume.side_effect = [
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'retyping', 'fake_type'),
            side_effect(volume, 'in-use', 'dest_type'),
        ]

        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util.check_volume_deleted = mock.MagicMock(return_value=True)
        result = cinder_util.check_retyped(volume, 'dest_type')
        self.assertEqual(mock_get_volume.call_count, 3)
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume)
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
        volume = self.fake_volume(
            status='in-use',
            migration_status='success',
            os_vol_host_attr_host='source_node',
        )

        def side_effect(volume, status, volume_type):
            result_volume = copy.deepcopy(volume)
            result_volume.status = status
            result_volume.volume_type = volume_type
            return result_volume

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
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume)
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
        volume = self.fake_volume(status='available')

        def side_effect(volume, status, volume_type):
            result_volume = copy.deepcopy(volume)
            result_volume.status = status
            result_volume.volume_type = volume_type
            return result_volume

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
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume)
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
        volume = self.fake_volume(status='in-use', migration_status='error')

        def side_effect(volume, status, volume_type):
            result_volume = copy.deepcopy(volume)
            result_volume.status = status
            result_volume.volume_type = volume_type
            return result_volume

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
        mock_log_debug.assert_any_call('Waiting the retype of %s', volume)
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
        pool = self.fake_pool(
            name='host@backend#pool',
            capabilities={'volume_backend_name': 'backend'},
        )
        volume_type1 = self.fake_volume_type(
            name='type_matching',
            extra_specs={'volume_backend_name': 'backend'},
        )
        volume_type2 = self.fake_volume_type(
            name='type_no_specs', extra_specs={}
        )
        cinder_util.cinder.volume_types.list.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool.to_dict())
        self.assertEqual(sorted(result), ['type_matching', 'type_no_specs'])

    def test_get_volume_types_for_pool_different_backend(self, mock_cinder):
        """Test different backend is excluded, no specs is included."""
        cinder_util = cinder_helper.CinderHelper()
        pool = self.fake_pool(
            name='host@backend#pool',
            capabilities={'volume_backend_name': 'backend'},
        )
        volume_type1 = self.fake_volume_type(
            name='type_no_specs', extra_specs={}
        )
        volume_type2 = self.fake_volume_type(
            name='type_different_backend',
            extra_specs={'volume_backend_name': 'different_backend'},
        )
        cinder_util.cinder.volume_types.list.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool.to_dict())
        self.assertEqual(result, ['type_no_specs'])

    def test_get_volume_types_for_pool_matching_capability(self, mock_cinder):
        """Test volume type with matching capability is selected."""
        cinder_util = cinder_helper.CinderHelper()
        pool = self.fake_pool(
            name='host@backend#pool', capabilities={'disk_speed': 'fast'}
        )
        volume_type = self.fake_volume_type(
            name='type_fast_disk', extra_specs={'disk_speed': 'fast'}
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool.to_dict())
        self.assertEqual(result, ['type_fast_disk'])

    def test_get_volume_types_for_pool_mismatched_capability(
        self, mock_cinder
    ):
        """Test volume type with different capability value excluded."""
        cinder_util = cinder_helper.CinderHelper()
        pool = self.fake_pool(
            name='host@backend#pool', capabilities={'disk_speed': 'fast'}
        )
        volume_type = self.fake_volume_type(
            name='type_slow_disk', extra_specs={'disk_speed': 'slow'}
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool.to_dict())
        self.assertEqual([], result)

    def test_get_volume_types_for_pool_no_capabilities(self, mock_cinder):
        """Test pool with no capabilities selects no-specs types."""
        cinder_util = cinder_helper.CinderHelper()
        pool = self.fake_pool(name='host@backend#pool', capabilities={})
        volume_type1 = self.fake_volume_type(
            name='type_no_specs', extra_specs={}
        )
        volume_type2 = self.fake_volume_type(
            name='type_with_specs',
            extra_specs={'volume_backend_name': 'backend'},
        )
        cinder_util.cinder.volume_types.list.return_value = [
            volume_type1,
            volume_type2,
        ]
        result = cinder_util.get_volume_types_for_pool(pool.to_dict())
        self.assertEqual(result, ['type_no_specs', 'type_with_specs'])

    def test_get_volume_types_for_pool_requirements_not_in_caps(
        self, mock_cinder
    ):
        """Test volume type with requirements not in pool capabilities."""
        cinder_util = cinder_helper.CinderHelper()
        pool = self.fake_pool(
            name='host@backend#pool',
            capabilities={'volume_backend_name': 'backend'},
        )
        volume_type = self.fake_volume_type(
            name='type_extra_reqs',
            extra_specs={
                'volume_backend_name': 'backend',
                'disk_speed': 'fast',
            },
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool.to_dict())
        self.assertEqual(result, ['type_extra_reqs'])

    def test_get_volume_types_for_pool_multiple_specs_partial_match(
        self, mock_cinder
    ):
        """Test volume type with multiple extra_specs partial match."""
        cinder_util = cinder_helper.CinderHelper()
        pool = self.fake_pool(
            name='host@backend#pool',
            capabilities={
                'volume_backend_name': 'backend',
                'disk_speed': 'fast',
                'compression': 'enabled',
            },
        )
        volume_type = self.fake_volume_type(
            name='type_partial',
            extra_specs={
                'volume_backend_name': 'backend',
                'disk_speed': 'slow',
                'compression': 'enabled',
            },
        )
        cinder_util.cinder.volume_types.list.return_value = [volume_type]
        result = cinder_util.get_volume_types_for_pool(pool.to_dict())
        self.assertEqual([], result)
