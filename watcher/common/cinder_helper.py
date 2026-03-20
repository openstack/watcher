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

from cinderclient import exceptions as cinder_exception
from cinderclient.v3.volumes import Volume
from oslo_log import log

from watcher import conf
from watcher._i18n import _
from watcher.common import clients
from watcher.common import exception


CONF = conf.CONF
LOG = log.getLogger(__name__)


class CinderHelper:
    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.cinder = self.osc.cinder()

    def get_storage_node_list(self):
        return list(self.cinder.services.list(binary='cinder-volume'))

    def get_storage_node_by_name(self, name):
        """Get storage node by name(host@backendname)"""
        try:
            storages = [
                storage
                for storage in self.get_storage_node_list()
                if storage.host == name
            ]
            if len(storages) != 1:
                raise exception.StorageNodeNotFound(name=name)
            return storages[0]
        except Exception as exc:
            LOG.exception(exc)
            raise exception.StorageNodeNotFound(name=name)

    def get_storage_pool_list(self):
        return self.cinder.pools.list(detailed=True)

    def get_storage_pool_by_name(self, name):
        """Get pool by name(host@backend#poolname)"""
        try:
            pools = [
                pool
                for pool in self.get_storage_pool_list()
                if pool.name == name
            ]
            if len(pools) != 1:
                raise exception.PoolNotFound(name=name)
            return pools[0]
        except Exception as exc:
            LOG.exception(exc)
            raise exception.PoolNotFound(name=name)

    def get_volume_list(self):
        return self.cinder.volumes.list(search_opts={'all_tenants': True})

    def get_volume_type_list(self):
        return self.cinder.volume_types.list()

    def get_volume_snapshots_list(self):
        return self.cinder.volume_snapshots.list(
            search_opts={'all_tenants': True}
        )

    def get_volume_type_by_backendname(self, backendname):
        """Return a list of volume type"""
        volume_type_list = self.get_volume_type_list()

        volume_type = [
            volume_type.name
            for volume_type in volume_type_list
            if volume_type.extra_specs.get('volume_backend_name')
            == backendname
        ]
        return volume_type

    def get_volume(self, volume):
        if isinstance(volume, Volume):
            volume = volume.id

        try:
            volume = self.cinder.volumes.get(volume)
            return volume
        except cinder_exception.NotFound:
            return self.cinder.volumes.find(name=volume)

    def _has_snapshot(self, volume):
        """Judge volume has a snapshot"""
        volume = self.get_volume(volume)
        if volume.snapshot_id:
            return True
        return False

    def get_deleting_volume(self, volume):
        volume = self.get_volume(volume)
        all_volume = self.get_volume_list()
        for _volume in all_volume:
            if getattr(_volume, 'os-vol-mig-status-attr:name_id') == volume.id:
                return _volume
        return False

    def _can_get_volume(self, volume_id):
        """Check to get volume with volume_id"""
        try:
            volume = self.get_volume(volume_id)
            if not volume:
                raise Exception
        except cinder_exception.NotFound:
            return False
        else:
            return True

    def _check_backend_matches_type(self, pool, volume_type):
        """Check if a storage pool matches volume type requirements.

        Verifies that all extra_specs properties defined in the volume
        type are present in the pool's capabilities with matching values.

        :param pool: Storage pool dictionary with capabilities
        :param volume_type: Volume type object with extra_specs
        :returns: True if pool matches all volume type requirements,
                  False otherwise
        """
        for field_name, field_value in volume_type.extra_specs.items():
            pool_value = pool.get("capabilities", {}).get(field_name)
            if pool_value is not None and field_value != pool_value:
                # the property associated with the volume type is
                # not defined in the pool, so the type can't be used in the
                # pool
                LOG.debug(
                    "property %s with value %s does not match value "
                    "%s from pool %s",
                    field_name,
                    field_value,
                    pool_value,
                    pool['name'],
                )
                return False
        return True

    def get_volume_types_for_pool(self, pool):
        """Return a list of volume types that can be associated with a pool.

        :param pool: Storage pool dictionary with capabilities
        :returns: List of volume types than can be scheduled in the input pool
        """
        volume_type_list = self.get_volume_type_list()

        pool_volume_types = []
        for volume_type in volume_type_list:
            if not volume_type.extra_specs:
                # if there are no properties associated with the volume type
                # it can be used in any pool
                pool_volume_types.append(volume_type.name)
                continue
            if self._check_backend_matches_type(pool, volume_type):
                pool_volume_types.append(volume_type.name)

        return pool_volume_types

    def check_volume_deleted(self, volume, retry=120, retry_interval=10):
        """Check volume has been deleted"""
        volume = self.get_volume(volume)
        while self._can_get_volume(volume.id) and retry:
            volume = self.get_volume(volume.id)
            time.sleep(retry_interval)
            retry -= 1
            LOG.debug("retry count: %s", retry)
            LOG.debug("Waiting to complete deletion of volume %s", volume.id)
        if self._can_get_volume(volume.id):
            LOG.error("Volume deletion error: %s", volume.id)
            return False

        LOG.debug("Volume %s was deleted successfully.", volume.id)
        return True

    def check_migrated(self, volume, retry_interval=10):
        volume = self.get_volume(volume)
        final_status = ('success', 'error')
        while getattr(volume, 'migration_status') not in final_status:
            volume = self.get_volume(volume.id)
            LOG.debug('Waiting the migration of %s', volume)
            time.sleep(retry_interval)
            if getattr(volume, 'migration_status') == 'error':
                host_name = getattr(volume, 'os-vol-host-attr:host')
                error_msg = (
                    "Volume migration error : "
                    f"volume {volume.id} is now on host "
                    f"'{host_name}'."
                )
                LOG.error(error_msg)
                return False

        host_name = getattr(volume, 'os-vol-host-attr:host')
        if getattr(volume, 'migration_status') == 'success':
            # check original volume deleted
            deleting_volume = self.get_deleting_volume(volume)
            if deleting_volume:
                delete_id = getattr(deleting_volume, 'id')
                if not self.check_volume_deleted(delete_id):
                    return False
        else:
            host_name = getattr(volume, 'os-vol-host-attr:host')
            error_msg = (
                "Volume migration error : "
                f"volume {volume.id} is now on host '{host_name}'."
            )
            LOG.error(error_msg)
            return False
        LOG.debug(
            "Volume migration succeeded : "
            "volume %(volume)s is now on host '%(host)s'.",
            {'volume': volume.id, 'host': host_name},
        )
        return True

    def check_retyped(self, volume, dst_type, retry_interval=10):
        volume = self.get_volume(volume)
        valid_status = ('available', 'in-use')
        # A volume retype is correct when the type is the dst_type
        # and the status is available or in-use. Otherwise, it is
        # in retyping status or the action failed
        while (
            volume.volume_type != dst_type or volume.status not in valid_status
        ):
            # Retype is not finished successfully, checking if the
            # retype is still ongoing or failed. If status is not
            # `retyping` it means something went wrong.
            if volume.status != 'retyping':
                LOG.error(
                    "Volume retype failed : "
                    "volume %(volume)s has now type '%(type)s' and "
                    "status %(status)s",
                    {
                        'volume': volume.id,
                        'type': volume.volume_type,
                        'status': volume.status,
                    },
                )
                # If migration_status is in error, a likely reason why the
                # retype failed is some problem in the migration. Report it in
                # the logs if migration_status is error.
                if volume.migration_status == 'error':
                    LOG.error(
                        "Volume migration error on volume %(volume)s.",
                        {'volume': volume.id},
                    )
                return False

            LOG.debug('Waiting the retype of %s', volume)
            time.sleep(retry_interval)
            volume = self.get_volume(volume.id)

        LOG.debug(
            "Volume retype succeeded : "
            "volume %(volume)s has now type '%(type)s'.",
            {'volume': volume.id, 'type': dst_type},
        )

        return True

    def migrate(self, volume, dest_node):
        """Migrate volume to dest_node"""
        volume = self.get_volume(volume)
        pool_dict = self.get_storage_pool_by_name(dest_node).to_dict()
        dest_types = self.get_volume_types_for_pool(pool_dict)
        if volume.volume_type not in dest_types:
            raise exception.Invalid(
                message=(
                    _(
                        "Volume type '%(volume_type)s' is not compatible with "
                        "destination pool '%(pool_name)s'"
                    )
                    % {
                        'volume_type': volume.volume_type,
                        'pool_name': dest_node,
                    }
                )
            )

        source_node = getattr(volume, 'os-vol-host-attr:host')
        LOG.debug(
            "Volume %(volume)s found on host '%(host)s'.",
            {'volume': volume.id, 'host': source_node},
        )

        self.cinder.volumes.migrate_volume(volume, dest_node, False, True)

        return self.check_migrated(volume)

    def retype(self, volume, dest_type):
        """Retype volume to dest_type with on-demand option"""
        volume = self.get_volume(volume)
        if volume.volume_type == dest_type:
            raise exception.Invalid(
                message=(_("Volume type must be different for retyping"))
            )

        source_node = getattr(volume, 'os-vol-host-attr:host')
        LOG.debug(
            "Volume %(volume)s found on host '%(host)s'.",
            {'volume': volume.id, 'host': source_node},
        )

        self.cinder.volumes.retype(volume, dest_type, "on-demand")

        return self.check_retyped(volume, dest_type)

    def create_volume(
        self, cinder, volume, dest_type, retry=120, retry_interval=10
    ):
        """Create volume of volume with dest_type using cinder"""
        volume = self.get_volume(volume)
        LOG.debug("start creating new volume")
        new_volume = cinder.volumes.create(
            getattr(volume, 'size'),
            name=getattr(volume, 'name'),
            volume_type=dest_type,
            availability_zone=getattr(volume, 'availability_zone'),
        )
        while getattr(new_volume, 'status') != 'available' and retry:
            new_volume = cinder.volumes.get(new_volume.id)
            LOG.debug('Waiting volume creation of %s', new_volume)
            time.sleep(retry_interval)
            retry -= 1
            LOG.debug("retry count: %s", retry)

        if getattr(new_volume, 'status') != 'available':
            error_msg = _("Failed to create volume '%(volume)s. ") % {
                'volume': new_volume.id
            }
            raise Exception(error_msg)

        LOG.debug("Volume %s was created successfully.", new_volume)
        return new_volume

    def delete_volume(self, volume):
        """Delete volume"""
        volume = self.get_volume(volume)
        self.cinder.volumes.delete(volume)
        result = self.check_volume_deleted(volume)
        if not result:
            error_msg = _("Failed to delete volume '%(volume)s. ") % {
                'volume': volume.id
            }
            raise Exception(error_msg)
