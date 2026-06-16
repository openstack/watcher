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
import functools
import time
import uuid

from cinderclient import exceptions as cinder_exception
from oslo_log import log

from watcher._i18n import _
from watcher.common import clients
from watcher.common import exception


LOG = log.getLogger(__name__)


def handle_cinder_error(resource_type, id_arg_index=1):
    """Decorator to handle exceptions from cinderclient.

    This decorator catches cinderclient exceptions and handles them
    as follows:
    - NotFound exceptions: logs a debug message and raises
      StorageResourceNotFound
    - Other cinderclient exceptions: re-raises as CinderClientError

    Use this for methods that call the Cinder API where a missing
    resource is a valid outcome but other errors should be propagated.

    :param resource_type: The type of resource being looked up
        (for logging)
    :param id_arg_index: The positional index of the resource ID
        argument (default 1, which is the first argument after self)
    :returns: Decorator function
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except cinder_exception.NotFound:
                if len(args) > id_arg_index:
                    resource_id = args[id_arg_index]
                else:
                    resource_id = 'unknown'
                LOG.debug("%s %s was not found", resource_type, resource_id)
                msg = f"{resource_id} of type {resource_type}"
                raise exception.StorageResourceNotFound(name=msg)
            except cinder_exception.ClientException as e:
                LOG.error("Cinder client error: %s", e)
                raise exception.CinderClientError(reason=str(e))

        return wrapper

    return decorator


@dc.dataclass(frozen=True)
class StorageService:
    """Pure dataclass for Cinder storage service data.

    Extracted from cinderclient Service object with all attributes
    resolved at construction time.
    """

    host: str
    zone: str
    state: str
    status: str

    @classmethod
    def from_cinderclient(cls, service):
        """Create from a cinderclient Service object.

        :param service: cinderclient Service object
        :returns: StorageService dataclass instance
        """
        return cls(
            host=service.host,
            zone=service.zone,
            state=service.state,
            status=service.status,
        )


@dc.dataclass
class StoragePool:
    """Pure dataclass for Cinder storage pool data.

    Extracted from cinderclient Pool object with all attributes
    resolved at construction time. Not frozen because
    storage_capacity_balance strategy mutates free_capacity_gb.
    """

    name: str
    pool_name: str | None
    total_volumes: int
    total_capacity_gb: float | None
    free_capacity_gb: float | None
    provisioned_capacity_gb: float | None
    allocated_capacity_gb: float | None
    max_over_subscription_ratio: float
    volume_backend_name: str | None
    capabilities: dict

    @classmethod
    def from_cinderclient(cls, pool):
        """Create from a cinderclient Pool object.

        :param pool: cinderclient Pool object (from detailed list)
        :returns: StoragePool dataclass instance
        """
        pool_dict = pool.to_dict()
        capabilities = pool_dict.get('capabilities', {})
        capacity_values = {}
        capacity_fields = [
            'total_capacity_gb',
            'free_capacity_gb',
            'provisioned_capacity_gb',
            'allocated_capacity_gb',
        ]
        for field in capacity_fields:
            value = capabilities.pop(field, None)
            if value == "unknown" or value is None:
                # NOTE (jgilaber) according to the cinder V3 api docs
                # https://docs.openstack.org/api-ref/block-storage/v3/index.html#back-end-storage-pools
                # the capacity values can be the string 'unknown'
                capacity_values[field] = None
            else:
                capacity_values[field] = float(value)
        return cls(
            name=pool.name,
            pool_name=pool_dict.get('pool_name'),
            total_volumes=pool_dict.get('total_volumes', 0),
            max_over_subscription_ratio=float(
                pool_dict.get('max_over_subscription_ratio', 1.0)
            ),
            volume_backend_name=pool_dict.get('volume_backend_name'),
            capabilities=capabilities,
            **capacity_values,
        )


@dc.dataclass(frozen=True)
class Volume:
    """Pure dataclass for Cinder volume data.

    Extracted from cinderclient Volume object with all attributes
    resolved at construction time. Hyphenated cinderclient
    attributes are mapped to valid Python field names.
    """

    id: str
    name: str
    size: int
    status: str
    volume_type: str
    attachments: list
    multiattach: bool
    metadata: dict
    bootable: str
    created_at: str
    tenant_id: str
    host: str | None
    migration_status: str | None
    name_id: str | None
    snapshot_id: str | None

    def __post_init__(self):
        """Validate UUID after initialization."""
        try:
            uuid.UUID(self.id)
        except ValueError:
            raise exception.InvalidUUID(uuid=self.id)

    @classmethod
    def from_cinderclient(cls, volume):
        """Create from a cinderclient Volume object.

        :param volume: cinderclient Volume object
        :returns: Volume dataclass instance
        """
        vol_dict = volume.to_dict()
        return cls(
            id=volume.id,
            name=volume.name,
            size=volume.size,
            status=volume.status,
            volume_type=volume.volume_type,
            attachments=volume.attachments,
            multiattach=volume.multiattach,
            snapshot_id=volume.snapshot_id,
            metadata=volume.metadata,
            bootable=volume.bootable,
            created_at=volume.created_at,
            migration_status=volume.migration_status,
            host=vol_dict.get('os-vol-host-attr:host'),
            tenant_id=vol_dict['os-vol-tenant-attr:tenant_id'],
            name_id=vol_dict.get('os-vol-mig-status-attr:name_id'),
        )


@dc.dataclass(frozen=True)
class VolumeType:
    """Pure dataclass for Cinder volume type data.

    Extracted from cinderclient VolumeType object with all
    attributes resolved at construction time.
    """

    id: str
    name: str
    extra_specs: dict

    def __post_init__(self):
        """Validate UUID after initialization."""
        try:
            uuid.UUID(self.id)
        except ValueError:
            raise exception.InvalidUUID(uuid=self.id)

    @classmethod
    def from_cinderclient(cls, volume_type):
        """Create from a cinderclient VolumeType object.

        :param volume_type: cinderclient VolumeType object
        :returns: VolumeType dataclass instance
        """
        return cls(
            id=volume_type.id,
            name=volume_type.name,
            extra_specs=volume_type.extra_specs,
        )


@dc.dataclass(frozen=True)
class VolumeSnapshot:
    """Pure dataclass for Cinder volume snapshot data.

    Extracted from cinderclient Snapshot object with all attributes
    resolved at construction time.
    """

    volume_id: str

    @classmethod
    def from_cinderclient(cls, snapshot):
        """Create from a cinderclient Snapshot object.

        :param snapshot: cinderclient Snapshot object
        :returns: VolumeSnapshot dataclass instance
        """
        return cls(volume_id=snapshot.volume_id)


class CinderHelper:
    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.cinder = self.osc.cinder()

    @handle_cinder_error("Storage service")
    def get_storage_node_list(self):
        return [
            StorageService.from_cinderclient(s)
            for s in self.cinder.services.list(binary='cinder-volume')
        ]

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

    @handle_cinder_error("Storage pool")
    def get_storage_pool_list(self):
        return [
            StoragePool.from_cinderclient(p)
            for p in self.cinder.pools.list(detailed=True)
        ]

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

    @handle_cinder_error("Volume")
    def get_volume_list(self):
        return [
            Volume.from_cinderclient(v)
            for v in self.cinder.volumes.list(
                search_opts={'all_tenants': True}
            )
        ]

    @handle_cinder_error("Volume type")
    def get_volume_type_list(self):
        return [
            VolumeType.from_cinderclient(vt)
            for vt in self.cinder.volume_types.list()
        ]

    def get_volume_type_name_by_id(self, volume_type_id):
        """Return the volume type name for a given volume type ID."""
        try:
            return self.cinder.volume_types.get(volume_type_id).name
        except cinder_exception.NotFound:
            raise exception.VolumeTypeNotFound(name=volume_type_id)

    @handle_cinder_error("Snapshot")
    def get_volume_snapshots_list(self):
        return [
            VolumeSnapshot.from_cinderclient(s)
            for s in self.cinder.volume_snapshots.list(
                search_opts={'all_tenants': True}
            )
        ]

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

    @handle_cinder_error("Volume")
    def get_volume(self, volume):
        if isinstance(volume, str):
            volume_id = volume
        else:
            volume_id = volume.id

        try:
            v = self.cinder.volumes.get(volume_id)
            return Volume.from_cinderclient(v)
        except cinder_exception.NotFound:
            v = self.cinder.volumes.find(name=volume_id)
            return Volume.from_cinderclient(v)

    def get_deleting_volume(self, volume):
        volume = self.get_volume(volume)
        all_volume = self.get_volume_list()
        for _volume in all_volume:
            if _volume.name_id == volume.id:
                return _volume
        return False

    def _can_get_volume(self, volume_id):
        """Check to get volume with volume_id"""
        try:
            volume = self.get_volume(volume_id)
            if not volume:
                raise exception.VolumeNotFound(name=volume_id)
        except exception.StorageResourceNotFound:
            return False
        else:
            return True

    def _check_backend_matches_type(self, pool, volume_type):
        """Check if a storage pool matches volume type requirements.

        Verifies that all extra_specs properties defined in the volume
        type are present in the pool's capabilities with matching values.

        :param pool: StoragePool dataclass instance
        :param volume_type: VolumeType dataclass instance
        :returns: True if pool matches all volume type requirements,
                  False otherwise
        """
        for field_name, field_value in volume_type.extra_specs.items():
            pool_value = pool.capabilities.get(field_name)
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
                    pool.name,
                )
                return False
        return True

    def get_volume_types_for_pool(self, pool):
        """Return a list of volume types that can be associated with a pool.

        :param pool: StoragePool dataclass instance
        :returns: List of volume types that can be scheduled in the input pool
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
        while volume.migration_status not in final_status:
            volume = self.get_volume(volume.id)
            LOG.debug('Waiting the migration of %s', volume.id)
            time.sleep(retry_interval)
            if volume.migration_status == 'error':
                error_msg = (
                    "Volume migration error : "
                    f"volume {volume.id} is now on host "
                    f"'{volume.host}'."
                )
                LOG.error(error_msg)
                return False

        if volume.migration_status == 'success':
            deleting_volume = self.get_deleting_volume(volume)
            if deleting_volume:
                if not self.check_volume_deleted(deleting_volume.id):
                    return False
        else:
            error_msg = (
                "Volume migration error : "
                f"volume {volume.id} is now on host "
                f"'{volume.host}'."
            )
            LOG.error(error_msg)
            return False
        LOG.debug(
            "Volume migration succeeded : "
            "volume %(volume)s is now on host '%(host)s'.",
            {'volume': volume.id, 'host': volume.host},
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

            LOG.debug('Waiting the retype of %s', volume.id)
            time.sleep(retry_interval)
            volume = self.get_volume(volume.id)

        LOG.debug(
            "Volume retype succeeded : "
            "volume %(volume)s has now type '%(type)s'.",
            {'volume': volume.id, 'type': dst_type},
        )

        return True

    @handle_cinder_error("Volume")
    def migrate(self, volume, dest_node):
        """Migrate volume to dest_node"""
        volume = self.get_volume(volume)
        pool = self.get_storage_pool_by_name(dest_node)
        dest_types = self.get_volume_types_for_pool(pool)
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

        LOG.debug(
            "Volume %(volume)s found on host '%(host)s'.",
            {'volume': volume.id, 'host': volume.host},
        )

        self.cinder.volumes.migrate_volume(volume.id, dest_node, False, True)

        return self.check_migrated(volume)

    @handle_cinder_error("Volume")
    def retype(self, volume, dest_type):
        """Retype volume to dest_type with on-demand option"""
        volume = self.get_volume(volume)
        if volume.volume_type == dest_type:
            raise exception.Invalid(
                message=(_("Volume type must be different for retyping"))
            )

        LOG.debug(
            "Volume %(volume)s found on host '%(host)s'.",
            {'volume': volume.id, 'host': volume.host},
        )

        self.cinder.volumes.retype(volume.id, dest_type, "on-demand")

        return self.check_retyped(volume, dest_type)
