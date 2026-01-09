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

from keystoneauth1 import exceptions as ksa_exc
from novaclient import api_versions
from oslo_log import log

import novaclient.exceptions as nvexceptions

from watcher.common import clients
from watcher.common import exception
from watcher import conf

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


@dc.dataclass(frozen=True)
class Server:
    """Pure dataclass for server data.

    Extracted from novaclient Server object with all extended attributes
    resolved at construction time.
    """

    id: str
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

    @classmethod
    def from_novaclient(cls, nova_server):
        """Create a Server dataclass from a novaclient Server object.

        :param nova_server: novaclient servers.Server object
        :returns: Server dataclass instance
        """
        server_dict = nova_server.to_dict()

        return cls(
            id=nova_server.id,
            name=nova_server.name,
            created=nova_server.created,
            host=server_dict.get('OS-EXT-SRV-ATTR:host'),
            vm_state=server_dict.get('OS-EXT-STS:vm_state'),
            task_state=server_dict.get('OS-EXT-STS:task_state'),
            power_state=server_dict.get('OS-EXT-STS:power_state'),
            status=nova_server.status,
            flavor=nova_server.flavor,
            tenant_id=nova_server.tenant_id,
            locked=nova_server.locked,
            metadata=nova_server.metadata,
            availability_zone=server_dict.get('OS-EXT-AZ:availability_zone'),
            pinned_availability_zone=server_dict.get(
                'pinned_availability_zone'
            )
        )


@dc.dataclass(frozen=True)
class Hypervisor:
    """Pure dataclass for hypervisor data.

    Extracted from novaclient Hypervisor object with all extended attributes
    resolved at construction time.
    """

    id: str
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

    @classmethod
    def from_novaclient(cls, nova_hypervisor):
        """Create a Hypervisor dataclass from a novaclient Hypervisor object.

        :param nova_hypervisor: novaclient hypervisors.Hypervisor object
        :returns: Hypervisor dataclass instance
        """
        hypervisor_dict = nova_hypervisor.to_dict()
        service = hypervisor_dict.get('service')
        service_host = None
        service_id = None
        service_disabled_reason = None
        if isinstance(service, dict):
            service_host = service.get('host')
            service_id = service.get('id')
            service_disabled_reason = service.get('disabled_reason')

        servers = hypervisor_dict.get('servers', [])

        return cls(
            id=nova_hypervisor.id,
            hypervisor_hostname=nova_hypervisor.hypervisor_hostname,
            hypervisor_type=nova_hypervisor.hypervisor_type,
            state=nova_hypervisor.state,
            status=nova_hypervisor.status,
            vcpus=hypervisor_dict.get('vcpus'),
            vcpus_used=hypervisor_dict.get('vcpus_used'),
            memory_mb=hypervisor_dict.get('memory_mb'),
            memory_mb_used=hypervisor_dict.get('memory_mb_used'),
            local_gb=hypervisor_dict.get('local_gb'),
            local_gb_used=hypervisor_dict.get('local_gb_used'),
            service_host=service_host,
            service_id=service_id,
            service_disabled_reason=service_disabled_reason,
            servers=servers,
        )


@dc.dataclass(frozen=True)
class Flavor:
    """Pure dataclass for flavor data.

    Extracted from novaclient Flavor object with all attributes
    resolved at construction time.
    """

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
    def from_novaclient(cls, nova_flavor):
        """Create a Flavor dataclass from a novaclient Flavor object.

        :param nova_flavor: novaclient flavors.Flavor object
        :returns: Flavor dataclass instance
        """
        swap = nova_flavor.swap
        if swap == "":
            swap = 0

        flavor_dict = nova_flavor.to_dict()

        return cls(
            id=nova_flavor.id,
            flavor_name=nova_flavor.name,
            vcpus=nova_flavor.vcpus,
            ram=nova_flavor.ram,
            disk=nova_flavor.disk,
            ephemeral=nova_flavor.ephemeral,
            swap=swap,
            is_public=nova_flavor.is_public,
            extra_specs=flavor_dict.get('extra_specs', {})
        )


@dc.dataclass(frozen=True)
class Aggregate:
    """Pure dataclass for aggregate data.

    Extracted from novaclient Aggregate object with all attributes
    resolved at construction time.
    """

    id: str
    name: str
    availability_zone: str | None
    hosts: list
    metadata: dict

    @classmethod
    def from_novaclient(cls, nova_aggregate):
        """Create an Aggregate dataclass from a novaclient Aggregate object.

        :param nova_aggregate: novaclient aggregates.Aggregate object
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

    Extracted from novaclient Service object with all attributes
    resolved at construction time.
    """

    id: str
    binary: str
    host: str
    zone: str
    status: str
    state: str
    updated_at: str | None
    disabled_reason: str | None

    @classmethod
    def from_novaclient(cls, nova_service):
        """Create a Service dataclass from a novaclient Service object.

        :param nova_service: novaclient services.Service object
        :returns: Service dataclass instance
        """
        return cls(
            id=nova_service.id,
            binary=nova_service.binary,
            host=nova_service.host,
            zone=nova_service.zone,
            status=nova_service.status,
            state=nova_service.state,
            updated_at=nova_service.updated_at,
            disabled_reason=nova_service.disabled_reason,
        )


@dc.dataclass(frozen=True)
class ServerMigration:
    """Pure dataclass for server migration data.

    Extracted from novaclient ServerMigration object with all attributes
    resolved at construction time.
    """

    id: str

    @classmethod
    def from_novaclient(cls, nova_migration):
        """Create a ServerMigration from a novaclient ServerMigration.

        :param nova_migration: novaclient server_migrations.ServerMigration
        :returns: ServerMigration dataclass instance
        """
        return cls(
            id=nova_migration.id,
        )


class NovaHelper:

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.cinder = self.osc.cinder()
        self.nova = self.osc.nova()
        self._is_pinned_az_available = None

    def is_pinned_az_available(self):
        """Check if pinned AZ is available in GET /servers/detail response.

        :returns: True if is available, False otherwise.
        """
        if self._is_pinned_az_available is None:
            self._is_pinned_az_available = (
                api_versions.APIVersion(
                    version_str=CONF.nova_client.api_version) >=
                api_versions.APIVersion(version_str='2.96'))
        return self._is_pinned_az_available

    @nova_retries
    def get_compute_node_list(self):
        hypervisors = self.nova.hypervisors.list()
        # filter out baremetal nodes from hypervisors
        compute_nodes = [node for node in hypervisors if
                         node.hypervisor_type != 'ironic']
        return compute_nodes

    @nova_retries
    def get_compute_node_by_name(self, node_name, servers=False,
                                 detailed=False):
        """Search for a hypervisor (compute node) by hypervisor_hostname

        :param node_name: The hypervisor_hostname to search
        :param servers: If true, include information about servers per
            hypervisor
        :param detailed: If true, include information about the compute service
            per hypervisor (requires microversion 2.53)
        """
        return self.nova.hypervisors.search(node_name, servers=servers,
                                            detailed=detailed)

    def get_compute_node_by_hostname(self, node_hostname):
        """Get compute node by hostname

        :param node_hostname: Compute service hostname
        :returns: novaclient.v2.hypervisors.Hypervisor object if found
        :raises: ComputeNodeNotFound if no hypervisor is found for the compute
            service hostname or there was an error communicating with nova
        """
        try:
            # This is a fuzzy match on hypervisor_hostname so we could get back
            # more than one compute node. If so, match on the compute service
            # hostname.
            compute_nodes = self.get_compute_node_by_name(
                node_hostname, detailed=True)
            for cn in compute_nodes:
                if cn.service['host'] == node_hostname:
                    return cn
            raise exception.ComputeNodeNotFound(name=node_hostname)
        except Exception as exc:
            LOG.exception(exc)
            raise exception.ComputeNodeNotFound(name=node_hostname)

    @nova_retries
    def get_compute_node_by_uuid(self, node_uuid):
        """Get compute node by uuid

        :param node_uuid: hypervisor id as uuid after microversion 2.53
        :returns: novaclient.v2.hypervisors.Hypervisor object if found
        """
        return self.nova.hypervisors.get(node_uuid)

    @nova_retries
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
        :returns: list of novaclient Server objects
        """
        search_opts = {'all_tenants': True}
        if filters:
            search_opts.update(filters)
        return self.nova.servers.list(search_opts=search_opts,
                                      marker=marker,
                                      limit=limit)

    @nova_retries
    def get_instance_by_uuid(self, instance_uuid):
        return [instance for instance in
                self.nova.servers.list(search_opts={"all_tenants": True,
                                                    "uuid": instance_uuid})]

    @nova_retries
    def get_flavor_list(self):
        return self.nova.flavors.list(**{'is_public': None})

    @nova_retries
    def get_flavor(self, flavor):
        return self.nova.flavors.get(flavor)

    @nova_retries
    def get_aggregate_list(self):
        return self.nova.aggregates.list()

    @nova_retries
    def get_aggregate_detail(self, aggregate_id):
        return self.nova.aggregates.get(aggregate_id)

    @nova_retries
    def get_service_list(self):
        return self.nova.services.list(binary='nova-compute')

    @nova_retries
    def find_instance(self, instance_id):
        return self.nova.servers.get(instance_id)

    @nova_retries
    def nova_start_instance(self, instance_id):
        return self.nova.servers.start(instance_id)

    @nova_retries
    def nova_stop_instance(self, instance_id):
        return self.nova.servers.stop(instance_id)

    @nova_retries
    def instance_resize(self, instance, flavor_id):
        return instance.resize(flavor=flavor_id)

    @nova_retries
    def instance_confirm_resize(self, instance):
        return instance.confirm_resize()

    @nova_retries
    def instance_live_migrate(self, instance, dest_hostname):
        # From nova api version 2.25(Mitaka release), the default value of
        # block_migration is None which is mapped to 'auto'.
        return instance.live_migrate(host=dest_hostname)

    @nova_retries
    def instance_migrate(self, instance, dest_hostname):
        return instance.migrate(host=dest_hostname)

    @nova_retries
    def live_migration_abort(self, instance_id, migration_id):
        return self.nova.server_migrations.live_migration_abort(
            server=instance_id, migration=migration_id)

    def confirm_resize(self, instance, previous_status, retry=60):
        self.instance_confirm_resize(instance)
        instance = self.find_instance(instance.id)
        while instance.status != previous_status and retry:
            instance = self.find_instance(instance.id)
            retry -= 1
            time.sleep(1)
        if instance.status == previous_status:
            return True
        else:
            LOG.debug("confirm resize failed for the "
                      "instance %s", instance.id)
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
            raise Exception(
                f"Volume {volume.id} did not reach status {status} "
                f"after {timeout:d} s")
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
        """
        LOG.debug(
            "Trying a cold migrate of instance '%s' ", instance_id)

        # Use config defaults if not provided in method parameters
        retry = retry or CONF.nova.migration_max_retries
        interval = interval or CONF.nova.migration_interval
        # Looking for the instance to migrate
        instance = self.find_instance(instance_id)
        if not instance:
            LOG.debug("Instance %s not found !", instance_id)
            return False
        else:
            host_name = getattr(instance, "OS-EXT-SRV-ATTR:host")
            LOG.debug(
                "Instance %(instance)s found on host '%(host)s'.",
                {'instance': instance_id, 'host': host_name})

            previous_status = getattr(instance, 'status')
            self.instance_migrate(instance, dest_hostname)
            instance = self.find_instance(instance_id)

            while (getattr(instance, 'status') not in
                   ["VERIFY_RESIZE", "ERROR"] and retry):
                instance = self.find_instance(instance.id)
                time.sleep(interval)
                retry -= 1
            new_hostname = getattr(instance, 'OS-EXT-SRV-ATTR:host')

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
        """
        LOG.debug(
            "Trying a resize of instance %(instance)s to "
            "flavor '%(flavor)s'",
            {'instance': instance_id, 'flavor': flavor})

        # Use config defaults if not provided in method parameters
        retry = retry or CONF.nova.migration_max_retries
        interval = interval or CONF.nova.migration_interval

        # Looking for the instance to resize
        instance = self.find_instance(instance_id)

        flavor_id = None

        try:
            flavor_id = self.get_flavor(flavor).id
        except nvexceptions.NotFound:
            flavor_id = [f.id for f in self.get_flavor_list() if
                         f.name == flavor][0]
        except nvexceptions.ClientException as e:
            LOG.debug("Nova client exception occurred while resizing "
                      "instance %s. Exception: %s", instance_id, e)

        if not flavor_id:
            LOG.debug("Flavor not found: %s", flavor)
            return False

        if not instance:
            LOG.debug("Instance not found: %s", instance_id)
            return False

        instance_status = getattr(instance, 'OS-EXT-STS:vm_state')
        LOG.debug(
            "Instance %(id)s is in '%(status)s' status.",
            {'id': instance_id, 'status': instance_status})

        self.instance_resize(instance, flavor_id)
        while getattr(instance,
                      'OS-EXT-STS:vm_state') != 'resized' \
                and retry:
            instance = self.find_instance(instance.id)
            LOG.debug('Waiting the resize of %s to %s', instance, flavor_id)
            time.sleep(interval)
            retry -= 1

        instance_status = getattr(instance, 'status')
        if instance_status != 'VERIFY_RESIZE':
            return False

        self.instance_confirm_resize(instance)

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
        """
        LOG.debug(
            "Trying a live migrate instance %(instance)s ",
            {'instance': instance_id})

        # Use config defaults if not provided in method parameters
        retry = retry or CONF.nova.migration_max_retries
        interval = interval or CONF.nova.migration_interval
        # Looking for the instance to migrate
        instance = self.find_instance(instance_id)
        if not instance:
            LOG.debug("Instance not found: %s", instance_id)
            return False
        else:
            host_name = getattr(instance, 'OS-EXT-SRV-ATTR:host')
            LOG.debug(
                "Instance %(instance)s found on host '%(host)s'.",
                {'instance': instance_id, 'host': host_name})

            self.instance_live_migrate(instance, dest_hostname)

            instance = self.find_instance(instance_id)

            # NOTE: If destination host is not specified for live migration
            # let nova scheduler choose the destination host.
            if dest_hostname is None:
                while (instance.status not in ['ACTIVE', 'ERROR'] and retry):
                    instance = self.find_instance(instance.id)
                    LOG.debug('Waiting the migration of %s', instance.id)
                    time.sleep(interval)
                    retry -= 1
                new_hostname = getattr(instance, 'OS-EXT-SRV-ATTR:host')

                if host_name != new_hostname and instance.status == 'ACTIVE':
                    LOG.debug(
                        "Live migration succeeded : "
                        "instance %(instance)s is now on host '%(host)s'.",
                        {'instance': instance_id, 'host': new_hostname})
                    return True
                else:
                    return False

            while getattr(instance,
                          'OS-EXT-SRV-ATTR:host') != dest_hostname \
                    and retry:
                instance = self.find_instance(instance.id)
                if not getattr(instance, 'OS-EXT-STS:task_state'):
                    LOG.debug("Instance task state: %s is null", instance_id)
                    break
                LOG.debug('Waiting the migration of %s to %s',
                          instance,
                          getattr(instance, 'OS-EXT-SRV-ATTR:host'))
                time.sleep(interval)
                retry -= 1

            host_name = getattr(instance, 'OS-EXT-SRV-ATTR:host')
            if host_name != dest_hostname:
                return False

            LOG.debug(
                "Live migration succeeded : "
                "instance %(instance)s is now on host '%(host)s'.",
                {'instance': instance_id, 'host': host_name})

            return True

    def abort_live_migrate(self, instance_id, source, destination, retry=240):
        LOG.debug("Aborting live migration of instance %s", instance_id)
        migration = self.get_running_migration(instance_id)
        if migration:
            migration_id = getattr(migration[0], "id")
            try:
                self.live_migration_abort(instance_id, migration_id)
            except exception as e:
                # Note: Does not return from here, as abort request can't be
                # accepted but migration still going on.
                LOG.exception(e)
        else:
            LOG.debug(
                "No running migrations found for instance %s", instance_id)

        while retry:
            instance = self.find_instance(instance_id)
            if (getattr(instance, 'OS-EXT-STS:task_state') is None and
               getattr(instance, 'status') in ['ACTIVE', 'ERROR']):
                break
            time.sleep(2)
            retry -= 1
        instance_host = getattr(instance, 'OS-EXT-SRV-ATTR:host')
        instance_status = getattr(instance, 'status')

        # Abort live migration successful, action is cancelled
        if instance_host == source and instance_status == 'ACTIVE':
            return True
        # Nova Unable to abort live migration, action is succeeded
        elif instance_host == destination and instance_status == 'ACTIVE':
            return False

        else:
            raise Exception("Live migration execution and abort both failed "
                            f"for the instance {instance_id}")

    @nova_retries
    def enable_service_nova_compute(self, hostname):
        if (api_versions.APIVersion(version_str=CONF.nova_client.api_version) <
                api_versions.APIVersion(version_str='2.53')):
            status = self.nova.services.enable(
                host=hostname, binary='nova-compute').status == 'enabled'
        else:
            service_uuid = self.nova.services.list(host=hostname,
                                                   binary='nova-compute')[0].id
            status = self.nova.services.enable(
                service_uuid=service_uuid).status == 'enabled'

        return status

    @nova_retries
    def disable_service_nova_compute(self, hostname, reason=None):
        if (api_versions.APIVersion(version_str=CONF.nova_client.api_version) <
                api_versions.APIVersion(version_str='2.53')):
            status = self.nova.services.disable_log_reason(
                host=hostname,
                binary='nova-compute',
                reason=reason).status == 'disabled'
        else:
            service_uuid = self.nova.services.list(host=hostname,
                                                   binary='nova-compute')[0].id
            status = self.nova.services.disable_log_reason(
                service_uuid=service_uuid,
                reason=reason).status == 'disabled'

        return status

    def stop_instance(self, instance_id):
        """This method stops a given instance.

        :param instance_id: the unique id of the instance to stop.
        """
        LOG.debug("Trying to stop instance %s ...", instance_id)

        instance = self.find_instance(instance_id)

        if not instance:
            LOG.debug("Instance not found: %s", instance_id)
            return False
        elif getattr(instance, 'OS-EXT-STS:vm_state') == "stopped":
            LOG.debug("Instance has been stopped: %s", instance_id)
            return True
        else:
            self.nova_stop_instance(instance_id)

            if self.wait_for_instance_state(instance, "stopped", 8, 10):
                LOG.debug("Instance %s stopped.", instance_id)
                return True
            else:
                return False

    def start_instance(self, instance_id):
        """This method starts a given instance.

        :param instance_id: the unique id of the instance to start.
        """
        LOG.debug("Trying to start instance %s ...", instance_id)

        instance = self.find_instance(instance_id)

        if not instance:
            LOG.debug("Instance not found: %s", instance_id)
            return False
        elif getattr(instance, 'OS-EXT-STS:vm_state') == "active":
            LOG.debug("Instance has already been started: %s", instance_id)
            return True
        else:
            self.nova_start_instance(instance_id)

            if self.wait_for_instance_state(instance, "active", 8, 10):
                LOG.debug("Instance %s started.", instance_id)
                return True
            else:
                return False

    def wait_for_instance_state(self, server, state, retry, sleep):
        """Waits for server to be in a specific state

        The state can be one of the following :
        active, stopped

        :param server: server object.
        :param state: for which state we are waiting for
        :param retry: how many times to retry
        :param sleep: seconds to sleep between the retries
        """
        if not server:
            return False

        while getattr(server, 'OS-EXT-STS:vm_state') != state and retry:
            time.sleep(sleep)
            server = self.find_instance(server)
            retry -= 1
        return getattr(server, 'OS-EXT-STS:vm_state') == state

    def get_hostname(self, instance):
        return str(getattr(instance, 'OS-EXT-SRV-ATTR:host'))

    @nova_retries
    def get_running_migration(self, instance_id):
        return self.nova.server_migrations.list(server=instance_id)

    def _check_nova_api_version(self, client, version):
        api_version = api_versions.APIVersion(version_str=version)
        try:
            api_versions.discover_version(client, api_version)
            return True
        except nvexceptions.UnsupportedVersion as e:
            LOG.exception(e)
            return False
