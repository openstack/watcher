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

from openstack import exceptions as sdk_exc
from oslo_log import log

from watcher import conf
from watcher._i18n import _
from watcher.common import base_helper
from watcher.common import exception


LOG = log.getLogger(__name__)
CONF = conf.CONF


def handle_cinder_error(resource_type, id_arg_index=1):
    """Decorator to handle exceptions from the block_storage proxy.

    This decorator catches the proxy exceptions and handles them as follows:
    - NotFound exceptions: logs a debug message and raises
      StorageResourceNotFound
    - Other block_storage proxy exceptions: re-raises as CinderClientError

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
            except sdk_exc.NotFoundException:
                if len(args) > id_arg_index:
                    resource_id = args[id_arg_index]
                else:
                    resource_id = 'unknown'
                LOG.debug("%s %s was not found", resource_type, resource_id)
                msg = f"{resource_id} of type {resource_type}"
                raise exception.StorageResourceNotFound(name=msg)
            except sdk_exc.SDKException as e:
                LOG.error("Cinder client error: %s", e)
                raise exception.CinderClientError(reason=str(e))

        return wrapper

    return decorator


@dc.dataclass(frozen=True)
class StorageService:
    """Pure dataclass for Cinder storage service data.

    Extracted from openstacksdk Service object with all attributes
    resolved at construction time.
    """

    host: str
    availability_zone: str
    state: str
    status: str

    @classmethod
    def from_openstacksdk(cls, service):
        """Create from an openstacksdk block_storage Service object.

        :param service: openstacksdk block_storage Service object
        :returns: StorageService dataclass instance
        """
        return cls(
            host=service.host,
            availability_zone=service.availability_zone,
            state=service.state,
            status=service.status,
        )


@dc.dataclass
class StoragePool:
    """Pure dataclass for Cinder storage pool data.

    Extracted from openstacksdk Pools object with all attributes
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
    def from_openstacksdk(cls, pool):
        """Create from an openstacksdk Pools object.

        :param pool: openstacksdk Pools object (from backend_pools())
        :returns: StoragePool dataclass instance
        """
        capabilities = pool.capabilities or {}
        capacity_fields = [
            'total_capacity_gb',
            'free_capacity_gb',
            'provisioned_capacity_gb',
            'allocated_capacity_gb',
        ]
        capacity_values = {}
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
            pool_name=capabilities.get('pool_name'),
            total_volumes=int(capabilities.get('total_volumes', 0) or 0),
            max_over_subscription_ratio=float(
                capabilities.get('max_over_subscription_ratio', 1.0)
            ),
            volume_backend_name=capabilities.get('volume_backend_name'),
            capabilities=capabilities,
            **capacity_values,
        )


@dc.dataclass(frozen=True)
class Volume:
    """Pure dataclass for Cinder volume data.

    Extracted from openstacksdk Volume object with all attributes
    resolved at construction time. Hyphenated openstacksdk JSON keys
    are mapped to clean Python field names.
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
    project_id: str
    host: str | None
    migration_status: str | None
    mig_name_id: str | None
    snapshot_id: str | None

    def __post_init__(self):
        """Validate UUID after initialization."""
        try:
            uuid.UUID(self.id)
        except ValueError:
            raise exception.InvalidUUID(uuid=self.id)

    @classmethod
    def from_openstacksdk(cls, volume):
        """Create from an openstacksdk Volume object.

        :param volume: openstacksdk Volume object
        :returns: Volume dataclass instance
        """
        return cls(
            id=volume.id,
            name=volume.name,
            size=volume.size,
            status=volume.status,
            volume_type=volume.volume_type,
            attachments=volume.attachments,
            multiattach=volume.is_multiattach,
            snapshot_id=volume.snapshot_id,
            metadata=volume.metadata,
            bootable=str(volume.is_bootable).lower(),
            created_at=str(volume.created_at),
            migration_status=volume.migration_status,
            host=volume.host,
            project_id=volume.project_id,
            mig_name_id=volume.migration_id,
        )


@dc.dataclass(frozen=True)
class VolumeType:
    """Pure dataclass for Cinder volume type data.

    Extracted from openstacksdk Type object with all
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
    def from_openstacksdk(cls, volume_type):
        """Create from an openstacksdk Type object.

        :param volume_type: openstacksdk Type object
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

    Extracted from openstacksdk Snapshot object with all attributes
    resolved at construction time.
    """

    volume_id: str

    @classmethod
    def from_openstacksdk(cls, snapshot):
        """Create from an openstacksdk Snapshot object.

        :param snapshot: openstacksdk Snapshot object
        :returns: VolumeSnapshot dataclass instance
        """
        return cls(volume_id=snapshot.volume_id)


class CinderHelper(base_helper.BaseConnectionMixin):
    def __init__(self, session=None, context=None):
        """Create a helper to call the cinder service.

        :param session: Optional keystone session to create
            the openstack connection.
        :param context: Optional context object, used to get
            user's token to create openstack connection.
        """
        self._config_overrides = False
        self._override_deprecated_configs()
        self._create_sdk_connection('cinder', context=context, session=session)

    def _override_deprecated_configs(self) -> None:
        """Apply deprecated cinder_client config overrides."""
        if self._config_overrides:
            return

        if (
            CONF.cinder.valid_interfaces is None
            and CONF.cinder.interface is None
        ):
            # NOTE(jgilaber): ensure the endpoint_type option from
            # cinder_client is processed and set with the right format in
            # [cinder] valid_interfaces, if the latter is not set
            endpoint_type = CONF.cinder_client.endpoint_type.replace('URL', '')
            CONF.set_override('valid_interfaces', [endpoint_type], 'cinder')

        self._config_overrides = True

    @handle_cinder_error("Storage service")
    def get_storage_node_list(self) -> list[StorageService]:
        """Return all cinder-volume storage services."""
        return [
            StorageService.from_openstacksdk(s)
            for s in self.connection.block_storage.services(
                binary='cinder-volume'
            )
        ]

    @handle_cinder_error("Storage service")
    def get_storage_node_by_name(self, name: str) -> StorageService:
        """Get a storage node by name.

        :param name: Storage node name (host@backendname).
        :returns: Matching storage service.
        :raises StorageNodeNotFound: If no unique match
            is found.
        """
        storages = [
            storage
            for storage in self.get_storage_node_list()
            if storage.host == name
        ]
        if len(storages) != 1:
            raise exception.StorageNodeNotFound(name=name)
        return storages[0]

    @handle_cinder_error("Storage pool")
    def get_storage_pool_list(self) -> list[StoragePool]:
        """Return all cinder backend storage pools."""
        return [
            StoragePool.from_openstacksdk(p)
            for p in self.connection.block_storage.backend_pools()
        ]

    @handle_cinder_error("Storage pool")
    def get_storage_pool_by_name(self, name: str) -> StoragePool:
        """Get a storage pool by name.

        :param name: Pool name (host@backend#poolname).
        :returns: Matching storage pool.
        :raises PoolNotFound: If no unique match is found.
        """
        pools = [
            pool for pool in self.get_storage_pool_list() if pool.name == name
        ]
        if len(pools) != 1:
            raise exception.PoolNotFound(name=name)
        return pools[0]

    @handle_cinder_error("Volume")
    def get_volume_list(self) -> list[Volume]:
        """Return all volumes across all projects."""
        return [
            Volume.from_openstacksdk(v)
            for v in self.connection.block_storage.volumes(all_projects=True)
        ]

    @handle_cinder_error("Volume type")
    def get_volume_type_list(self) -> list[VolumeType]:
        """Return all volume types."""
        return [
            VolumeType.from_openstacksdk(vt)
            for vt in self.connection.block_storage.types()
        ]

    def get_volume_type_name_by_id(self, volume_type_id: str) -> str:
        """Return the volume type name for a given volume type ID."""
        try:
            return self.connection.block_storage.get_type(volume_type_id).name
        except sdk_exc.NotFoundException:
            raise exception.VolumeTypeNotFound(name=volume_type_id)

    @handle_cinder_error("Snapshot")
    def get_volume_snapshots_list(self) -> list[VolumeSnapshot]:
        """Return all volume snapshots across all projects."""
        return [
            VolumeSnapshot.from_openstacksdk(s)
            for s in self.connection.block_storage.snapshots(all_projects=True)
        ]

    def get_volume_type_by_backendname(self, backendname: str) -> list[str]:
        """Return volume type names for a backend.

        :param backendname: The volume backend name to match.
        :returns: List of volume type names whose
            ``volume_backend_name`` extra spec matches.
        """
        volume_type_list = self.get_volume_type_list()

        volume_type = [
            volume_type.name
            for volume_type in volume_type_list
            if volume_type.extra_specs.get('volume_backend_name')
            == backendname
        ]
        return volume_type

    @handle_cinder_error("Volume")
    def get_volume(self, volume: str | Volume) -> Volume:
        """Get a volume by ID or Volume object.

        :param volume: Volume ID string or Volume instance.
        :returns: The retrieved volume.
        """
        if isinstance(volume, str):
            volume_id = volume
        else:
            volume_id = volume.id

        try:
            v = self.connection.block_storage.get_volume(volume_id)
            return Volume.from_openstacksdk(v)
        except sdk_exc.NotFoundException:
            v = self.connection.block_storage.find_volume(
                volume_id, ignore_missing=False
            )
            return Volume.from_openstacksdk(v)

    def get_deleting_volume(self, volume: str | Volume) -> Volume | bool:
        """Get the shadow volume being deleted after migration.

        :param volume: Volume ID string or Volume instance.
        :returns: The deleting shadow volume, or False if
            not found.
        """
        volume = self.get_volume(volume)
        all_volume = self.get_volume_list()
        for _volume in all_volume:
            if _volume.mig_name_id == volume.id:
                return _volume
        return False

    def _can_get_volume(self, volume_id: str) -> bool:
        """Check whether a volume can be retrieved.

        :param volume_id: The volume ID to look up.
        :returns: True if the volume exists, False otherwise.
        """
        try:
            self.get_volume(volume_id)
        except exception.StorageResourceNotFound:
            return False
        return True

    def _check_backend_matches_type(
        self, pool: StoragePool, volume_type: VolumeType
    ) -> bool:
        """Check if a pool matches volume type requirements.

        Verifies that all extra_specs properties defined in the
        volume type are present in the pool's capabilities with
        matching values.

        :param pool: StoragePool dataclass instance.
        :param volume_type: VolumeType dataclass instance.
        :returns: True if pool matches all volume type
            requirements, False otherwise.
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

    def get_volume_types_for_pool(self, pool: StoragePool) -> list[str]:
        """Return a list of volume types that can be associated with a pool.

        :param pool: StoragePool dataclass instance.
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

    def check_volume_deleted(
        self, volume: str | Volume, retry: int = 120, retry_interval: int = 10
    ) -> bool:
        """Wait for a volume to be deleted.

        :param volume: Volume ID string or Volume instance.
        :param retry: Maximum number of polling attempts.
        :param retry_interval: Seconds between attempts.
        :returns: True if deleted, False on timeout.
        """
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

    def check_migrated(
        self, volume: str | Volume, retry_interval: int = 10
    ) -> bool:
        """Wait for volume migration to complete.

        :param volume: Volume ID string or Volume instance.
        :param retry_interval: Seconds between poll attempts.
        :returns: True if migration succeeded, False on error.
        """
        volume = self.get_volume(volume)
        final_status = ('success', 'error')
        while volume.migration_status not in final_status:
            volume = self.get_volume(volume.id)
            LOG.debug('Waiting the migration of %s', volume.id)
            time.sleep(retry_interval)
            if volume.migration_status == 'error':
                LOG.error(
                    "Volume migration error : "
                    "volume %(volume)s is now on host '%(host)s'.",
                    {'volume': volume.id, 'host': volume.host},
                )
                return False

        if volume.migration_status == 'success':
            deleting_volume = self.get_deleting_volume(volume)
            if deleting_volume:
                if not self.check_volume_deleted(deleting_volume.id):
                    return False
        else:
            LOG.error(
                "Volume migration error : "
                "volume %(volume)s is now on host '%(host)s'.",
                {'volume': volume.id, 'host': volume.host},
            )
            return False
        LOG.debug(
            "Volume migration succeeded : "
            "volume %(volume)s is now on host '%(host)s'.",
            {'volume': volume.id, 'host': volume.host},
        )
        return True

    def check_retyped(
        self, volume: str | Volume, dst_type: str, retry_interval: int = 10
    ) -> bool:
        """Wait for volume retype to complete.

        :param volume: Volume ID string or Volume instance.
        :param dst_type: Target volume type name.
        :param retry_interval: Seconds between poll attempts.
        :returns: True if retype succeeded, False on error.
        """
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
    def migrate(self, volume: str | Volume, dest_node: str) -> bool:
        """Migrate a volume to a destination node.

        :param volume: Volume ID string or Volume instance.
        :param dest_node: Destination pool name
            (host@backend#pool).
        :returns: True if migration succeeded, False on error.
        :raises Invalid: If the volume type is incompatible
            with the destination pool.
        """
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

        self.connection.block_storage.migrate_volume(
            volume.id, host=dest_node, force_host_copy=False, lock_volume=True
        )

        return self.check_migrated(volume)

    @handle_cinder_error("Volume")
    def retype(self, volume: str | Volume, dest_type: str) -> bool:
        """Retype a volume with on-demand migration policy.

        :param volume: Volume ID string or Volume instance.
        :param dest_type: Target volume type name.
        :returns: True if retype succeeded, False on error.
        :raises Invalid: If the volume already has the target
            type.
        """
        volume = self.get_volume(volume)
        if volume.volume_type == dest_type:
            raise exception.Invalid(
                message=(_("Volume type must be different for retyping"))
            )

        LOG.debug(
            "Volume %(volume)s found on host '%(host)s'.",
            {'volume': volume.id, 'host': volume.host},
        )

        self.connection.block_storage.retype_volume(
            volume.id, new_type=dest_type, migration_policy="on-demand"
        )

        return self.check_retyped(volume, dest_type)
