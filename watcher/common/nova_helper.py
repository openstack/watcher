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

import dataclasses as dc
import functools
import time
import uuid

from keystoneauth1 import exceptions as ksa_exc
from keystoneauth1 import loading as ks_loading
import microversion_parse
from openstack import exceptions as sdk_exc
from oslo_log import log
from watcher.common import clients
from watcher.common import exception
from watcher import conf
from watcher.conf import clients_auth

LOG = log.getLogger(__name__)

CONF = conf.CONF


def nova_retries(call):
    @functools.wraps(call)
    def wrapper(*args, **kwargs):
        retries = CONF.nova.http_retries
        retry_interval = CONF.nova.http_retry_interval
        for i in range(retries + 1):
            try:
                return call(*args, **kwargs)
            except ksa_exc.ConnectionError as e:
                LOG.warning('Error connecting to Nova service: %s', e)
                if i < retries:
                    LOG.warning('Retrying connection to Nova service')
                    time.sleep(retry_interval)
                else:
                    LOG.error(
                        'Failed to connect to Nova service after %d attempts',
                        retries + 1)
                    raise
    return wrapper


def handle_nova_error(resource_type, id_arg_index=1):
    """Decorator to handle exceptions from novaclient.

    This decorator catches novaclient exceptions and handles them as follows:
    - NotFound exceptions: logs a debug message and raises
      ComputeResourceNotFound
    - Other novaclient exceptions: re-raises as NovaClientError

    Use this for methods that retrieve individual resources by ID where a
    missing resource is a valid outcome but other errors should be propagated.

    :param resource_type: The type of resource being looked up (for logging)
    :param id_arg_index: The positional index of the resource ID argument
        (default 1, which is the first argument after self)
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
                raise exception.ComputeResourceNotFound(msg)
            except sdk_exc.SDKException as e:
                LOG.error("Nova client error: %s", e)
                raise exception.NovaClientError(reason=str(e))
        return wrapper
    return decorator


@dc.dataclass(frozen=True)
class Server:
    """Pure dataclass for server data.

    Extracted from OpenStackSDK Server object with all attributes
    resolved at construction time.
    """

    uuid: str
    name: str
    created: str
    host: str | None
    vm_state: str | None
    task_state: str | None
    power_state: int | None
    status: str
    flavor: dict
    tenant_id: str
    locked: bool
    metadata: dict
    availability_zone: str | None
    pinned_availability_zone: str | None

    def __post_init__(self):
        """Validate UUID after initialization."""
        try:
            uuid.UUID(self.uuid)
        except ValueError:
            raise exception.InvalidUUID(uuid=self.uuid)

    @classmethod
    def from_openstacksdk(cls, nova_server):
        """Create a Server dataclass from a OpenStackSDK Server object.

        :param nova_server: OpenStackSDK Server object
        :returns: Server dataclass instance
        :raises: InvalidUUID if server ID is not a valid UUID
        """
        return cls(
            uuid=nova_server.id,
            name=nova_server.name,
            created=nova_server.created_at,
            host=nova_server.compute_host,
            vm_state=nova_server.vm_state,
            task_state=nova_server.task_state,
            power_state=nova_server.power_state,
            status=nova_server.status,
            flavor=nova_server.flavor,
            tenant_id=nova_server.project_id,
            locked=nova_server.is_locked,
            metadata=nova_server.metadata,
            availability_zone=nova_server.availability_zone,
            pinned_availability_zone=nova_server.pinned_availability_zone
        )


@dc.dataclass(frozen=True)
class Hypervisor:
    """Pure dataclass for hypervisor data.

    Extracted from OpenStackSDK Hypervisor object with all attributes
    resolved at construction time.
    """

    uuid: str
    hypervisor_hostname: str
    hypervisor_type: str
    state: str
    status: str
    vcpus: int | None
    vcpus_used: int | None
    memory_mb: int | None
    memory_mb_used: int | None
    local_gb: int | None
    local_gb_used: int | None
    service_host: str | None
    service_id: str | None
    service_disabled_reason: str | None
    servers: list | None

    def __post_init__(self):
        """Validate UUID after initialization."""
        try:
            uuid.UUID(self.uuid)
        except ValueError:
            raise exception.InvalidUUID(uuid=self.uuid)

    @classmethod
    def from_openstacksdk(cls, nova_hypervisor):
        """Create a Hypervisor dataclass from a OpenStackSDK Hypervisor object.

        :param nova_hypervisor: OpenStackSDK Hypervisor object
        :returns: Hypervisor dataclass instance
        :raises: InvalidUUID if hypervisor ID is not a valid UUID
        """
        service = nova_hypervisor.service_details
        service_host = None
        service_id = None
        service_disabled_reason = None
        if isinstance(service, dict):
            service_host = service.get('host')
            service_id = service.get('id')
            service_disabled_reason = service.get('disabled_reason')

        servers = nova_hypervisor.servers
        if servers is None:
            servers = []

        return cls(
            uuid=nova_hypervisor.id,
            hypervisor_hostname=nova_hypervisor.name,
            hypervisor_type=nova_hypervisor.hypervisor_type,
            state=nova_hypervisor.state,
            status=nova_hypervisor.status,
            vcpus=nova_hypervisor.vcpus,
            vcpus_used=nova_hypervisor.vcpus_used,
            memory_mb=nova_hypervisor.memory_size,
            memory_mb_used=nova_hypervisor.memory_used,
            local_gb=nova_hypervisor.local_disk_size,
            local_gb_used=nova_hypervisor.local_disk_used,
            service_host=service_host,
            service_id=service_id,
            service_disabled_reason=service_disabled_reason,
            servers=servers,
        )


@dc.dataclass(frozen=True)
class Flavor:
    """Pure dataclass for flavor data.

    Extracted from OpenStackSDK Flavor object with all attributes
    resolved at construction time.
    """

    # as opposed to Server or Hypervisor, the Flavor id is not a uuid, but a
    # string containing an integer
    id: str
    flavor_name: str
    vcpus: int
    ram: int
    disk: int
    ephemeral: int
    swap: int
    is_public: bool
    extra_specs: dict

    @classmethod
    def from_openstacksdk(cls, nova_flavor):
        """Create a Flavor dataclass from a OpenStackSDK Flavor object.

        :param nova_flavor: OpenStackSDK Flavor object
        :returns: Flavor dataclass instance
        """

        return cls(
            id=nova_flavor.id,
            flavor_name=nova_flavor.name,
            vcpus=nova_flavor.vcpus,
            ram=nova_flavor.ram,
            disk=nova_flavor.disk,
            ephemeral=nova_flavor.ephemeral,
            swap=nova_flavor.swap,
            is_public=nova_flavor.is_public,
            extra_specs=nova_flavor.extra_specs
        )


@dc.dataclass(frozen=True)
class Aggregate:
    """Pure dataclass for aggregate data.

    Extracted from OpenStackSDK Aggregate object with all attributes
    resolved at construction time.
    """

    # as opposed to Server or Hypervisor, the Aggregate id is not a uuid, but a
    # string containing an integer
    id: str
    name: str
    availability_zone: str | None
    hosts: list
    metadata: dict

    @classmethod
    def from_openstacksdk(cls, nova_aggregate):
        """Create an Aggregate dataclass from a OpenStackSDK Aggregate object.

        :param nova_aggregate: OpenStackSDK Aggregate object
        :returns: Aggregate dataclass instance
        """
        return cls(
            id=nova_aggregate.id,
            name=nova_aggregate.name,
            availability_zone=nova_aggregate.availability_zone,
            hosts=nova_aggregate.hosts,
            metadata=nova_aggregate.metadata,
        )


@dc.dataclass(frozen=True)
class Service:
    """Pure dataclass for service data.

    Extracted from OpenStackSDK Service object with all attributes
    resolved at construction time.
    """

    uuid: str
    binary: str
    host: str
    zone: str
    status: str
    state: str
    updated_at: str | None
    disabled_reason: str | None

    def __post_init__(self):
        """Validate UUID after initialization."""
        try:
            uuid.UUID(self.uuid)
        except ValueError:
            raise exception.InvalidUUID(uuid=self.uuid)

    @classmethod
    def from_openstacksdk(cls, nova_service):
        """Create a Service dataclass from a OpenStackSDK Service object.

        :param nova_service: OpenStackSDK Service object
        :returns: Service dataclass instance
        :raises: InvalidUUID if service ID is not a valid UUID
        """
        return cls(
            uuid=nova_service.id,
            binary=nova_service.binary,
            host=nova_service.host,
            zone=nova_service.availability_zone,
            status=nova_service.status,
            state=nova_service.state,
            updated_at=nova_service.updated_at,
            disabled_reason=nova_service.disabled_reason,
        )


@dc.dataclass(frozen=True)
class ServerMigration:
    """Pure dataclass for server migration data.

    Extracted from OpenStackSDK ServerMigration object with all attributes
    resolved at construction time.
    """

    # as opposed to Server or Hypervisor, the ServerMigration id is not a
    # uuid, but a string containing an integer
    id: str

    @classmethod
    def from_openstacksdk(cls, nova_migration):
        """Create a ServerMigration from a OpenStackSDK ServerMigration.

        :param nova_migration: OpenStackSDK ServerMigration
        :returns: ServerMigration dataclass instance
        """
        return cls(
            id=nova_migration.id,
        )


class NovaHelper:

    def __init__(self, osc=None, session=None, context=None):
        """Create and return a helper to call the nova service

        :param osc: an OpenStackClients instance
        :param session: Optional keystone session to create the openstack
        connection.
        :param context: Optional context object, use to get user's token to
        create openstack connection.
        """
        self._config_overrides = False
        self._override_deprecated_configs()
        clients.check_min_nova_api_version(CONF.nova.api_version)
        self.osc = osc if osc else clients.OpenStackClients()
        self.cinder = self.osc.cinder()
        self._create_sdk_connection(
            context=context, session=session
        )
        self._is_pinned_az_available = None

    def _override_deprecated_configs(self):
        if self._config_overrides:
            return

        if CONF.nova.valid_interfaces is None and CONF.nova.interface is None:
            # NOTE(jgilaber): ensure the endpoint_type option from nova_client
            # is processed and set with the right format in [nova]
            # valid_interfaces, if the latter is not set in the configuration
            endpoint_type = CONF.nova_client.endpoint_type.replace('URL', '')
            CONF.set_override('valid_interfaces', [endpoint_type], 'nova')

        self._config_overrides = True

    def _create_sdk_connection(self, session=None, context=None):
        """Create and return an OpenStackSDK Connection

        :param session: Optional keystone session to create the openstack
        connection.
        :param context: Optional context object, use to get user's token to
        create openstack connection.
        """
        auth_group = 'nova'
        nova_auth = ks_loading.load_auth_from_conf_options(CONF, 'nova')
        if nova_auth is None:
            # NOTE(jgilaber): if can't configure the auth from the values in
            # [nova], use [watcher_clients_auth] as fallback
            LOG.debug(
                "could not load auth plugin from [nova] section, using %s "
                "as fallback", clients_auth.WATCHER_CLIENTS_AUTH
            )
            auth_group = clients_auth.WATCHER_CLIENTS_AUTH

        self.connection = clients.get_sdk_connection(
            auth_group, context=context, session=session,
            interface=CONF.nova.valid_interfaces,
            region_name=CONF.nova.region_name
        )

    def is_pinned_az_available(self):
        """Check if pinned AZ is available in GET /servers/detail response.

        :returns: True if is available, False otherwise.
        """
        if self._is_pinned_az_available is None:
            configured_version = microversion_parse.parse_version_string(
                CONF.nova.api_version
            )
            pinned_version = microversion_parse.parse_version_string('2.96')
            self._is_pinned_az_available = configured_version >= pinned_version
        return self._is_pinned_az_available

    @nova_retries
    @handle_nova_error("Compute node")
    def get_compute_node_list(self, filter_ironic_nodes=True):
        """Get the list of compute nodes (hypervisors).

        :param filter_ironic_nodes: If True, exclude baremetal (ironic) nodes
            from the returned list. Defaults to True.
        :returns: List of Hypervisor objects.
        """
        hypervisors = self.connection.compute.hypervisors(details=True)
        # filter out baremetal nodes from hypervisors
        compute_nodes = [
            Hypervisor.from_openstacksdk(node) for node in hypervisors
        ]
        if filter_ironic_nodes:
            compute_nodes = [
                node for node in compute_nodes
                if node.hypervisor_type != 'ironic'
            ]
        return compute_nodes

    @nova_retries
    @handle_nova_error("Compute node")
    def get_compute_node_by_name(self, node_name, servers=False,
                                 detailed=False):
        """Search for a hypervisor (compute node) by hypervisor_hostname

        :param node_name: The hypervisor_hostname to search
        :param servers: If true, include information about servers per
            hypervisor
        :param detailed: If true, include information about the compute service
            per hypervisor (requires microversion 2.53)
        :returns: list of Hypervisor wrapper objects or None if no hypervisor
        is found
        """
        # SDK hypervisors() method returns all hypervisors, filter by name
        hypervisors = self.connection.compute.hypervisors(
            hypervisor_hostname_pattern=node_name, with_servers=servers,
            details=detailed)
        return [Hypervisor.from_openstacksdk(h) for h in hypervisors]

    def get_compute_node_by_hostname(self, node_hostname):
        """Get compute node by hostname

        :param node_hostname: Compute service hostname
        :returns: Hypervisor object if found
        :raises: ComputeNodeNotFound if no hypervisor is found for the compute
            service hostname or there was an error communicating with nova
        """
        try:
            # This is a fuzzy match on hypervisor_hostname so we could get back
            # more than one compute node. If so, match on the compute service
            # hostname.
            compute_nodes = self.get_compute_node_by_name(
                node_hostname, detailed=True)
            if compute_nodes:
                for cn in compute_nodes:
                    if cn.service_host == node_hostname:
                        return cn
            raise exception.ComputeNodeNotFound(name=node_hostname)
        except Exception as exc:
            LOG.exception(exc)
            raise exception.ComputeNodeNotFound(name=node_hostname) from exc

    @nova_retries
    @handle_nova_error("Compute node")
    def get_compute_node_by_uuid(self, node_uuid):
        """Get compute node by uuid

        :param node_uuid: hypervisor id as uuid after microversion 2.53
        :returns: Hypervisor wrapper object if found, None if not found
        """
        hypervisor = self.connection.compute.get_hypervisor(node_uuid)
        return Hypervisor.from_openstacksdk(hypervisor)

    @nova_retries
    @handle_nova_error("Instance")
    def get_instance_list(self, filters=None, marker=None, limit=-1):
        """List servers for all tenants with details.

        This always gets servers with the all_tenants=True filter.

        :param filters: Dict of additional filters (optional).
        :param marker: Get servers that appear later in the server
                       list than that represented by this server id (optional).
        :param limit: Maximum number of servers to return (optional).
                      If limit == -1, all servers will be returned,
                      note that limit == -1 will have a performance
                      penalty. For details, please see:
                      https://bugs.launchpad.net/watcher/+bug/1834679
        :returns: list of Server wrapper objects
        """
        query_params = {
            'all_projects': True, 'marker': marker
        }
        if limit != -1:
            query_params['limit'] = limit
        if filters:
            if 'host' in filters:
                # NOTE(jgilaber) openstacksdk servers module uses
                # 'compute_host' as the name for the host query filter,
                # passing 'host' is simply ignored
                filters['compute_host'] = filters.pop('host')
            query_params.update(filters)
        servers = self.connection.compute.servers(details=True,
                                                  **query_params)
        return [Server.from_openstacksdk(s) for s in servers]

    @nova_retries
    @handle_nova_error("Instance")
    def get_instance_by_uuid(self, instance_uuid):
        """Get an instance matching the given UUID.

        :param instance_uuid: the UUID of the instance to search for
        :returns: Server wrapper object matching the UUID
        :raises: ComputeResourceNotFound if no instance was found
        """
        servers = self.connection.compute.servers(details=True,
                                                  all_projects=True,
                                                  uuid=instance_uuid)
        if servers:
            return Server.from_openstacksdk(servers[0])
        else:
            msg = f"{instance_uuid} of type Instance"
            raise exception.ComputeResourceNotFound(msg)

    @nova_retries
    @handle_nova_error("Flavor list")
    def get_flavor_list(self):
        """Get the list of all flavors including private ones.

        :returns: list of Flavor wrapper objects
        """
        flavors = self.connection.compute.flavors(is_public=None)
        return [Flavor.from_openstacksdk(f) for f in flavors]

    @nova_retries
    @handle_nova_error("Flavor")
    def _get_flavor(self, flavor):
        """Get a flavor by ID or name.

        :param flavor: the ID or name of the flavor to get
        :returns: Flavor wrapper object if found, None if not found
        """
        return Flavor.from_openstacksdk(
            self.connection.compute.get_flavor(flavor)
        )

    @nova_retries
    @handle_nova_error("Aggregate")
    def get_aggregate_list(self):
        """Get the list of all host aggregates.

        :returns: list of Aggregate wrapper objects
        """
        aggregates = self.connection.compute.aggregates()
        return [Aggregate.from_openstacksdk(a) for a in aggregates]

    @nova_retries
    @handle_nova_error("Aggregate")
    def get_aggregate_detail(self, aggregate_id):
        """Get details of a specific host aggregate.

        :param aggregate_id: the ID of the aggregate to get
        :returns: Aggregate wrapper object if found, None if not found
        """
        return Aggregate.from_openstacksdk(
            self.connection.compute.get_aggregate(aggregate_id))

    @nova_retries
    @handle_nova_error("Service")
    def get_service_list(self):
        """Get the list of all nova-compute services.

        :returns: list of Service wrapper objects
        """
        services = self.connection.compute.services(binary='nova-compute')
        return [Service.from_openstacksdk(s) for s in services]

    @nova_retries
    @handle_nova_error("Instance")
    def find_instance(self, instance_id):
        """Find an instance by its ID.

        :param instance_id: the UUID of the instance to find
        :returns: Server wrapper object if found, None if not found
        """
        instance = self.connection.compute.get_server(instance_id)
        return Server.from_openstacksdk(instance)

    @nova_retries
    @handle_nova_error("Instance")
    def _nova_start_instance(self, instance_id):
        """Start an instance via Nova API.

        :param instance_id: the UUID of the instance to start
        """
        return self.connection.compute.start_server(instance_id)

    @nova_retries
    @handle_nova_error("Instance")
    def _nova_stop_instance(self, instance_id):
        """Stop an instance via Nova API.

        :param instance_id: the UUID of the instance to stop
        """
        return self.connection.compute.stop_server(instance_id)

    @nova_retries
    @handle_nova_error("Instance")
    def _instance_resize(self, instance, flavor_id):
        """Resize an instance to a new flavor via Nova API.

        :param instance: the instance ID or Server object to resize
        :param flavor_id: the ID of the target flavor
        """
        return self.connection.compute.resize_server(instance, flavor_id)

    @nova_retries
    @handle_nova_error("Instance")
    def _instance_confirm_resize(self, instance):
        """Confirm a pending resize operation via Nova API.

        :param instance: the instance ID or Server object to confirm resize
        """
        return self.connection.compute.confirm_server_resize(instance)

    @nova_retries
    @handle_nova_error("Instance")
    def _instance_live_migrate(self, instance, dest_hostname):
        """Initiate a live migration of an instance via Nova API.

        :param instance: the instance ID or Server object to migrate
        :param dest_hostname: the destination compute node hostname
        """

        # From Nova API version 2.25 (Mitaka release), the default value of
        # block_migration is None which is mapped to 'auto'.
        return self.connection.compute.live_migrate_server(
            instance, host=dest_hostname, block_migration='auto'
        )

    @nova_retries
    @handle_nova_error("Instance")
    def _instance_migrate(self, instance, dest_hostname):
        """Initiate a cold migration of an instance via Nova API.

        :param instance: the instance ID or Server object to migrate
        :param dest_hostname: the destination compute node hostname
        """
        return self.connection.compute.migrate_server(
            instance, host=dest_hostname
        )

    @nova_retries
    @handle_nova_error("Instance")
    def _live_migration_abort(self, instance_id, migration_id):
        """Abort an in-progress live migration via Nova API.

        :param instance_id: the UUID of the instance being migrated
        :param migration_id: the ID of the migration to abort
        """
        return self.connection.compute.abort_server_migration(
            migration_id, instance_id
        )

    def confirm_resize(self, instance, previous_status, retry=60):
        """Confirm a resize operation and wait for the instance status.

        :param instance: Server wrapper object of the instance
        :param previous_status: the expected status after confirmation
        :param retry: number of retries to wait for the expected status
        :returns: True if confirmation succeeded and status matches,
            False otherwise
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        instance_id = instance.uuid
        self._instance_confirm_resize(instance_id)
        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug(
                "Instance %s was not found, could not confirm its resize",
                instance_id
            )
            return False

        while instance.status != previous_status and retry:
            try:
                instance = self.find_instance(instance_id)
            except exception.ComputeResourceNotFound:
                LOG.debug(
                    "Instance %s was not found, could not confirm its resize",
                    instance_id
                )
                return False
            retry -= 1
            time.sleep(1)
        if instance.status == previous_status:
            return True
        else:
            LOG.debug("confirm resize failed for the "
                      "instance %s", instance_id)
            return False

    def wait_for_volume_status(self, volume, status, timeout=60,
                               poll_interval=1):
        """Wait until volume reaches given status.

        :param volume: volume resource
        :param status: expected status of volume
        :param timeout: timeout in seconds
        :param poll_interval: poll interval in seconds
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            volume = self.cinder.volumes.get(volume.id)
            if volume.status == status:
                break
            time.sleep(poll_interval)
        else:
            raise exception.VolumeNotReachedStatus(
                volume.id,
                status
            )
        return volume.status == status

    def watcher_non_live_migrate_instance(self, instance_id, dest_hostname,
                                          retry=None, interval=None):
        """This method migrates a given instance

        This method uses the Nova built-in migrate()
        action to do a migration of a given instance.
        For migrating a given dest_hostname, Nova API version
        must be 2.56 or higher.

        It returns True if the migration was successful,
        False otherwise.

        :param instance_id: the unique id of the instance to migrate.
        :param dest_hostname: the name of the destination compute node, if
                              destination_node is None, nova scheduler choose
                              the destination host
        :param retry: maximum number of retries before giving up
        :param interval: interval in seconds between retries
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        LOG.debug(
            "Trying a cold migrate of instance '%s' ", instance_id)

        # Use config defaults if not provided in method parameters
        retry = retry or CONF.nova.migration_max_retries
        interval = interval or CONF.nova.migration_interval
        # Looking for the instance to migrate
        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug(
                "Instance %s not found, can't cold migrate it.", instance_id
            )
            return False
        host_name = instance.host
        LOG.debug(
            {'instance': instance_id, 'host': host_name})

        previous_status = instance.status
        self._instance_migrate(instance_id, dest_hostname)
        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug(
                "Instance %s not found, can't cold migrate it.", instance_id
            )
            return False

        while (instance.status not in
                ["VERIFY_RESIZE", "ERROR"] and retry):
            try:
                instance = self.find_instance(instance_id)
            except exception.ComputeResourceNotFound:
                LOG.debug(
                    "Instance %s not found, can't cold migrate it.",
                    instance_id
                )
                return False
            time.sleep(interval)
            retry -= 1
        new_hostname = instance.host

        if (host_name != new_hostname and
                instance.status == 'VERIFY_RESIZE'):
            if not self.confirm_resize(instance, previous_status):
                return False
            LOG.debug(
                "cold migration succeeded : "
                "instance %(instance)s is now on host '%(host)s'.",
                {'instance': instance_id, 'host': new_hostname})
            return True
        else:
            LOG.debug(
                "cold migration for instance %s failed", instance_id)
            return False

    def resize_instance(self, instance_id, flavor, retry=None, interval=None):
        """This method resizes given instance with specified flavor.

        This method uses the Nova built-in resize()
        action to do a resize of a given instance.

        It returns True if the resize was successful,
        False otherwise.

        :param instance_id: the unique id of the instance to resize.
        :param flavor: the name or ID of the flavor to resize to.
        :param retry: maximum number of retries before giving up
        :param interval: interval in seconds between retries
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        LOG.debug(
            "Trying a resize of instance %(instance)s to "
            "flavor '%(flavor)s'",
            {'instance': instance_id, 'flavor': flavor})

        # Use config defaults if not provided in method parameters
        retry = retry or CONF.nova.migration_max_retries
        interval = interval or CONF.nova.migration_interval

        # Looking for the instance to resize
        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug("Instance not found: %s, could not resize", instance_id)
            return False

        flavor_id = None

        try:
            try:
                flavor_obj = self._get_flavor(flavor)
                flavor_id = flavor_obj.id
            except exception.ComputeResourceNotFound:
                flavor_id = next((f.id for f in self.get_flavor_list() if
                                  f.flavor_name == flavor), None)
        except exception.NovaClientError as e:
            LOG.debug("Nova client exception occurred while resizing "
                      "instance %s. Exception: %s", instance_id, e)

        if not flavor_id:
            LOG.debug("Flavor not found: %s, could not resize", flavor)
            return False

        instance_status = instance.vm_state
        LOG.debug(
            "Instance %(id)s is in '%(status)s' status.",
            {'id': instance_id, 'status': instance_status})

        self._instance_resize(instance_id, flavor_id)
        while instance.vm_state != 'resized' and retry:
            try:
                instance = self.find_instance(instance_id)
            except exception.ComputeResourceNotFound:
                LOG.debug(
                    "Instance not found: %s, could not resize", instance_id
                )
                return False
            LOG.debug('Waiting the resize of %s to %s', instance, flavor_id)
            time.sleep(interval)
            retry -= 1

        instance_status = instance.status
        if instance_status != 'VERIFY_RESIZE':
            return False

        self._instance_confirm_resize(instance_id)

        LOG.debug("Resizing succeeded : instance %s is now on flavor "
                  "'%s'.", instance_id, flavor_id)

        return True

    def live_migrate_instance(self, instance_id, dest_hostname, retry=None,
                              interval=None):
        """This method does a live migration of a given instance

        This method uses the Nova built-in live_migrate()
        action to do a live migration of a given instance.

        It returns True if the migration was successful,
        False otherwise.

        :param instance_id: the unique id of the instance to migrate.
        :param dest_hostname: the name of the destination compute node, if
                              destination_node is None, nova scheduler choose
                              the destination host
        :param retry: maximum number of retries before giving up
        :param interval: interval in seconds between retries
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        LOG.debug(
            "Trying a live migrate instance %(instance)s ",
            {'instance': instance_id})

        # Use config defaults if not provided in method parameters
        retry = retry or CONF.nova.migration_max_retries
        interval = interval or CONF.nova.migration_interval
        # Looking for the instance to migrate
        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug("Instance %s not found, can't live migrate", instance_id)
            return False

        host_name = instance.host
        LOG.debug(
            "Instance %(instance)s found on host '%(host)s'.",
            {'instance': instance_id, 'host': host_name})

        self._instance_live_migrate(instance_id, dest_hostname)

        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug("Instance %s not found!", instance_id)
            return False

        # NOTE: If destination host is not specified for live migration
        # let nova scheduler choose the destination host.
        if dest_hostname is None:
            while (instance.status not in ['ACTIVE', 'ERROR'] and retry):
                try:
                    instance = self.find_instance(instance_id)
                except exception.ComputeResourceNotFound:
                    LOG.debug(
                        "Instance %s not found, can't live migrate",
                        instance_id
                    )
                    return False
                LOG.debug('Waiting the migration of %s', instance_id)
                time.sleep(interval)
                retry -= 1
            new_hostname = instance.host

            if host_name != new_hostname and instance.status == 'ACTIVE':
                LOG.debug(
                    "Live migration succeeded : "
                    "instance %(instance)s is now on host '%(host)s'.",
                    {'instance': instance_id, 'host': new_hostname})
                return True
            else:
                return False

        while instance.host != dest_hostname and retry:
            try:
                instance = self.find_instance(instance_id)
            except exception.ComputeResourceNotFound:
                LOG.debug("Instance %s not found!", instance_id)
                return False
            if not instance.task_state:
                LOG.debug("Instance task state: %s is null", instance_id)
                break
            LOG.debug(
                'Waiting the migration of %s to %s', instance, instance.host
                )
            time.sleep(interval)
            retry -= 1

        host_name = instance.host
        if host_name != dest_hostname:
            return False

        LOG.debug(
            "Live migration succeeded : "
            "instance %(instance)s is now on host '%(host)s'.",
            {'instance': instance_id, 'host': host_name})

        return True

    def abort_live_migrate(self, instance_id, source, destination, retry=240):
        """Abort an in-progress live migration of an instance.

        :param instance_id: the UUID of the instance being migrated
        :param source: the source compute node hostname
        :param destination: the destination compute node hostname
        :param retry: number of retries to wait for the abort to complete
        :returns: True if abort succeeded (instance on source), False if
            migration completed (instance on destination)
        :raises: LiveMigrationFailed if instance ends up in error state
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        LOG.debug("Aborting live migration of instance %s", instance_id)
        migration = None
        try:
            migration = self.get_running_migration(instance_id)
        except exception.ComputeResourceNotFound:
            # failed to abort the migration since the migration does not exist
            LOG.debug(
                "No running migrations found for instance %s", instance_id)
        if migration:
            migration_id = migration[0].id
            try:
                self._live_migration_abort(instance_id, migration_id)
            except (exception.ComputeResourceNotFound,
                    exception.NovaClientError) as e:
                # Note: Does not return from here, as abort request can't be
                # accepted but migration still going on.
                LOG.exception(e)

        while retry:
            try:
                instance = self.find_instance(instance_id)
            except exception.ComputeResourceNotFound:
                LOG.debug(
                    "Instance %s not found, can't abort live migrate",
                    instance_id
                )
                return False
            if (instance.task_state is None and
               instance.status in ['ACTIVE', 'ERROR']):
                break
            time.sleep(2)
            retry -= 1
        instance_host = instance.host
        instance_status = instance.status

        # Abort live migration successful, action is canceled
        if instance_host == source and instance_status == 'ACTIVE':
            return True
        # Nova Unable to abort live migration, action is succeeded
        elif instance_host == destination and instance_status == 'ACTIVE':
            return False
        else:
            raise exception.LiveMigrationFailed(instance_id)

    @nova_retries
    @handle_nova_error("Service")
    def enable_service_nova_compute(self, hostname):
        """Enable the nova-compute service on a given host.

        :param hostname: the hostname of the compute service to enable
        :returns: True if service is now enabled, False otherwise
        """
        services = list(
            self.connection.compute.services(
                host=hostname, binary='nova-compute'
            )
        )
        if not services:
            LOG.debug("No nova-compute service found at %s", hostname)
            return False
        service = services[0]
        updated_service = self.connection.compute.enable_service(service.id)
        return updated_service.status == 'enabled'

    @nova_retries
    @handle_nova_error("Service")
    def disable_service_nova_compute(self, hostname, reason=None):
        """Disable the nova-compute service on a given host.

        :param hostname: the hostname of the compute service to disable
        :param reason: optional reason for disabling the service
        :returns: True if service is now disabled, False otherwise
        """
        services = list(
            self.connection.compute.services(
                host=hostname, binary='nova-compute'
            )
        )
        if not services:
            LOG.debug("No nova-compute service found at %s", hostname)
            return False
        service = services[0]
        updated_service = self.connection.compute.disable_service(
            service.id, disabled_reason=reason
        )
        return updated_service.status == 'disabled'

    def stop_instance(self, instance_id):
        """This method stops a given instance.

        :param instance_id: the unique id of the instance to stop.
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        LOG.debug("Trying to stop instance %s ...", instance_id)

        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug("Instance not found: %s, can't stop it", instance_id)
            return False

        if instance.vm_state == "stopped":
            LOG.debug("Instance has been stopped: %s", instance_id)
            return True
        else:
            self._nova_stop_instance(instance_id)

            if self.wait_for_instance_state(instance, "stopped", 8, 10):
                LOG.debug("Instance %s stopped.", instance_id)
                return True
            else:
                return False

    def start_instance(self, instance_id):
        """This method starts a given instance.

        :param instance_id: the unique id of the instance to start.
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        LOG.debug("Trying to start instance %s ...", instance_id)

        try:
            instance = self.find_instance(instance_id)
        except exception.ComputeResourceNotFound:
            LOG.debug("Instance not found: %s, can't start it", instance_id)
            return False

        if instance.vm_state == "active":
            LOG.debug("Instance has already been started: %s", instance_id)
            return True
        else:
            self._nova_start_instance(instance_id)

            if self.wait_for_instance_state(instance, "active", 8, 10):
                LOG.debug("Instance %s started.", instance_id)
                return True
            else:
                return False

    def wait_for_instance_state(self, server, state, retry, sleep):
        """Waits for server to be in a specific state

        The state can be one of the following :
        active, stopped

        :param server: Server wrapper object.
        :param state: for which state we are waiting for
        :param retry: how many times to retry
        :param sleep: seconds to sleep between the retries
        :raises: NovaClientError if there is any problem while calling the Nova
        api
        """
        if not server:
            return False

        while server.vm_state != state and retry:
            time.sleep(sleep)
            server_id = server.uuid
            try:
                server = self.find_instance(server.uuid)
            except exception.ComputeResourceNotFound:
                LOG.debug(
                    "Instance not found: %s, can't wait for status", server_id
                )
                return False
            retry -= 1
        return server.vm_state == state

    def get_hostname(self, instance):
        """Get the hostname of the compute node hosting an instance.

        :param instance: Server wrapper object
        :returns: the hostname of the compute node
        """
        return instance.host

    @nova_retries
    @handle_nova_error("Instance")
    def get_running_migration(self, instance_id):
        """Get the list of running migrations for an instance.

        :param instance_id: the UUID of the instance
        :returns: list of ServerMigration wrapper objects
        :raises: ComputeResourceNotFound if there is no instance with id
        instance_id
        """
        migrations = self.connection.compute.server_migrations(instance_id)
        return [ServerMigration.from_openstacksdk(m) for m in migrations]
