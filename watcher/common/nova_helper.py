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

import time

from novaclient import api_versions
from oslo_log import log

import novaclient.exceptions as nvexceptions

from watcher.common import clients
from watcher.common import exception
from watcher import conf

LOG = log.getLogger(__name__)

CONF = conf.CONF


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

    def get_compute_node_list(self):
        hypervisors = self.nova.hypervisors.list()
        # filter out baremetal nodes from hypervisors
        compute_nodes = [node for node in hypervisors if
                         node.hypervisor_type != 'ironic']
        return compute_nodes

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

    def get_compute_node_by_uuid(self, node_uuid):
        """Get compute node by uuid

        :param node_uuid: hypervisor id as uuid after microversion 2.53
        :returns: novaclient.v2.hypervisors.Hypervisor object if found
        """
        return self.nova.hypervisors.get(node_uuid)

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

    def get_instance_by_uuid(self, instance_uuid):
        return [instance for instance in
                self.nova.servers.list(search_opts={"all_tenants": True,
                                                    "uuid": instance_uuid})]

    def get_flavor_list(self):
        return self.nova.flavors.list(**{'is_public': None})

    def get_aggregate_list(self):
        return self.nova.aggregates.list()

    def get_aggregate_detail(self, aggregate_id):
        return self.nova.aggregates.get(aggregate_id)

    def get_service_list(self):
        return self.nova.services.list(binary='nova-compute')

    def find_instance(self, instance_id):
        return self.nova.servers.get(instance_id)

    def confirm_resize(self, instance, previous_status, retry=60):
        instance.confirm_resize()
        instance = self.nova.servers.get(instance.id)
        while instance.status != previous_status and retry:
            instance = self.nova.servers.get(instance.id)
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
                                          retry=120):
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
        """
        LOG.debug(
            "Trying a cold migrate of instance '%s' ", instance_id)

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
            instance.migrate(host=dest_hostname)
            instance = self.nova.servers.get(instance_id)

            while (getattr(instance, 'status') not in
                   ["VERIFY_RESIZE", "ERROR"] and retry):
                instance = self.nova.servers.get(instance.id)
                time.sleep(2)
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

    def resize_instance(self, instance_id, flavor, retry=120):
        """This method resizes given instance with specified flavor.

        This method uses the Nova built-in resize()
        action to do a resize of a given instance.

        It returns True if the resize was successful,
        False otherwise.

        :param instance_id: the unique id of the instance to resize.
        :param flavor: the name or ID of the flavor to resize to.
        """
        LOG.debug(
            "Trying a resize of instance %(instance)s to "
            "flavor '%(flavor)s'",
            {'instance': instance_id, 'flavor': flavor})

        # Looking for the instance to resize
        instance = self.find_instance(instance_id)

        flavor_id = None

        try:
            flavor_id = self.nova.flavors.get(flavor).id
        except nvexceptions.NotFound:
            flavor_id = [f.id for f in self.nova.flavors.list() if
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

        instance.resize(flavor=flavor_id)
        while getattr(instance,
                      'OS-EXT-STS:vm_state') != 'resized' \
                and retry:
            instance = self.nova.servers.get(instance.id)
            LOG.debug('Waiting the resize of %s to %s', instance, flavor_id)
            time.sleep(1)
            retry -= 1

        instance_status = getattr(instance, 'status')
        if instance_status != 'VERIFY_RESIZE':
            return False

        instance.confirm_resize()

        LOG.debug("Resizing succeeded : instance %s is now on flavor "
                  "'%s'.", instance_id, flavor_id)

        return True

    def live_migrate_instance(self, instance_id, dest_hostname, retry=120):
        """This method does a live migration of a given instance

        This method uses the Nova built-in live_migrate()
        action to do a live migration of a given instance.

        It returns True if the migration was successful,
        False otherwise.

        :param instance_id: the unique id of the instance to migrate.
        :param dest_hostname: the name of the destination compute node, if
                              destination_node is None, nova scheduler choose
                              the destination host
        """
        LOG.debug(
            "Trying a live migrate instance %(instance)s ",
            {'instance': instance_id})

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

            # From nova api version 2.25(Mitaka release), the default value of
            # block_migration is None which is mapped to 'auto'.
            instance.live_migrate(host=dest_hostname)

            instance = self.nova.servers.get(instance_id)

            # NOTE: If destination host is not specified for live migration
            # let nova scheduler choose the destination host.
            if dest_hostname is None:
                while (instance.status not in ['ACTIVE', 'ERROR'] and retry):
                    instance = self.nova.servers.get(instance.id)
                    LOG.debug('Waiting the migration of %s', instance.id)
                    time.sleep(1)
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
                instance = self.nova.servers.get(instance.id)
                if not getattr(instance, 'OS-EXT-STS:task_state'):
                    LOG.debug("Instance task state: %s is null", instance_id)
                    break
                LOG.debug('Waiting the migration of %s to %s',
                          instance,
                          getattr(instance, 'OS-EXT-SRV-ATTR:host'))
                time.sleep(1)
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
                self.nova.server_migrations.live_migration_abort(
                    server=instance_id, migration=migration_id)
            except exception as e:
                # Note: Does not return from here, as abort request can't be
                # accepted but migration still going on.
                LOG.exception(e)
        else:
            LOG.debug(
                "No running migrations found for instance %s", instance_id)

        while retry:
            instance = self.nova.servers.get(instance_id)
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
            self.nova.servers.stop(instance_id)

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
            self.nova.servers.start(instance_id)

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
            server = self.nova.servers.get(server)
            retry -= 1
        return getattr(server, 'OS-EXT-STS:vm_state') == state

    def get_hostname(self, instance):
        return str(getattr(instance, 'OS-EXT-SRV-ATTR:host'))

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
