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

from unittest import mock

from http import HTTPStatus
import time

from cinderclient import exceptions as cinder_exception

from watcher.common import cinder_helper
from watcher.common import clients
from watcher.common import exception
from watcher.common import utils
from watcher.tests import base


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
            binary='cinder-volume')

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
            cinder_util.get_storage_node_by_name, 'failure')

    @staticmethod
    def fake_pool(**kwargs):
        pool = mock.MagicMock()
        pool.name = kwargs.get('name', 'host@backend#pool')

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
            cinder_util.get_storage_pool_by_name, 'failure')

    @staticmethod
    def fake_volume_type(**kwargs):
        volume_type = mock.MagicMock()
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
            self, mock_cinder):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'backend')

        self.assertEqual(volume_type_name[0], volume_type1.name)

    def test_get_volume_type_by_backendname_with_no_backend_exist(
            self, mock_cinder):
        volume_type1 = self.fake_volume_type()
        cinder_util = cinder_helper.CinderHelper()
        cinder_util.cinder.volume_types.list.return_value = [volume_type1]
        volume_type_name = cinder_util.get_volume_type_by_backendname(
            'nobackend')

        self.assertEqual([], volume_type_name)

    @staticmethod
    def fake_volume(**kwargs):
        volume = mock.MagicMock()
        volume.id = kwargs.get('id', '45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba')
        volume.name = kwargs.get('name', 'fakename')
        volume.size = kwargs.get('size', '1')
        volume.status = kwargs.get('status', 'available')
        volume.snapshot_id = kwargs.get('snapshot_id', None)
        volume.availability_zone = kwargs.get('availability_zone', 'nova')
        volume.volume_type = kwargs.get('volume_type', 'fake_type')
        return volume

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_migrate_success(self, mock_cinder):

        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'migration_status', 'success')
        cinder_util.cinder.volumes.get.return_value = volume

        volume_type = self.fake_volume_type()
        cinder_util.cinder.volume_types.list.return_value = [volume_type]

        result = cinder_util.migrate(volume, 'host@backend#pool')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_migrate_fail(self, mock_cinder):

        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume

        volume_type = self.fake_volume_type()
        volume_type.name = 'notbackend'
        cinder_util.cinder.volume_types.list.return_value = [volume_type]

        self.assertRaisesRegex(
            exception.Invalid,
            "Volume type must be same for migrating",
            cinder_util.migrate, volume, 'host@backend#pool')

        volume = self.fake_volume()
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'migration_status', 'error')
        cinder_util.cinder.volumes.get.return_value = volume

        volume_type = self.fake_volume_type()
        cinder_util.cinder.volume_types.list.return_value = [volume_type]

        result = cinder_util.migrate(volume, 'host@backend#pool')
        self.assertFalse(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_retype_success(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'migration_status', 'success')
        cinder_util.cinder.volumes.get.return_value = volume

        result = cinder_util.retype(volume, 'notfake_type')
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_retype_fail(self, mock_cinder):
        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'migration_status', 'success')
        cinder_util.cinder.volumes.get.return_value = volume

        self.assertRaisesRegex(
            exception.Invalid,
            "Volume type must be different for retyping",
            cinder_util.retype, volume, 'fake_type')

        volume = self.fake_volume()
        setattr(volume, 'os-vol-host-attr:host', 'source_node')
        setattr(volume, 'migration_status', 'error')
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
            cinder_util.cinder, volume, 'fake_type')
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
            cinder_util.create_volume, cinder_util.cinder, volume,
            'fake_type', retry=2, retry_interval=1)

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
            volume)

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
        cinder_util.get_volume.side_effect =\
            cinder_exception.NotFound(HTTPStatus.NOT_FOUND)
        result = cinder_util._can_get_volume(volume.id)
        self.assertFalse(result)

        cinder_util.get_volume = mock.MagicMock(return_value=None)
        self.assertRaises(
            Exception,
            cinder_util._can_get_volume,
            volume.id)

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
            volume, retry=2, retry_interval=1)
        self.assertTrue(result)

    @mock.patch.object(time, 'sleep', mock.Mock())
    def test_check_volume_deleted_fail(self, mock_cinder):

        cinder_util = cinder_helper.CinderHelper()

        volume = self.fake_volume()
        cinder_util.cinder.volumes.get.return_value = volume
        cinder_util._can_get_volume = mock.MagicMock(return_value=volume)
        result = cinder_util.check_volume_deleted(
            volume, retry=2, retry_interval=1)
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
