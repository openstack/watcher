# Copyright 2026 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

"""Utilities for Watcher tests of code from the common module."""

from novaclient.v2 import aggregates
from novaclient.v2 import flavors
from novaclient.v2 import hypervisors
from novaclient.v2 import server_migrations
from novaclient.v2 import servers
from novaclient.v2 import services


class NovaResourcesMixin:
    def create_nova_server(self, **kwargs):
        """Create a real novaclient Server object.

        :param kwargs: additional server attributes
        :returns: novaclient.v2.servers.Server object
        """
        server_info = {
            'id': kwargs.pop('id', 'd010ef1f-dc19-4982-9383-087498bfde03'),
            'name': kwargs.pop('name', 'test-server'),
            'status': kwargs.pop('status', 'ACTIVE'),
            'created': kwargs.pop('created', '2026-01-09T12:00:00Z'),
            'tenant_id': kwargs.pop('tenant_id', 'test-tenant-id'),
            'locked': kwargs.pop('locked', False),
            'metadata': kwargs.pop('metadata', {}),
            'flavor': kwargs.pop('flavor', {'id': 'flavor-1'}),
            'pinned_availability_zone': kwargs.pop(
                'pinned_availability_zone', None),
        }
        server_info.update(kwargs)
        return servers.Server(servers.ServerManager, info=server_info)

    def create_nova_hypervisor(self, **kwargs):
        """Create a real novaclient Hypervisor object.

        :param kwargs: additional hypervisor attributes
        :returns: novaclient.v2.hypervisors.Hypervisor object
        """
        hostname = kwargs.pop('hostname', 'hypervisor-hostname')
        hypervisor_info = {
            'id': kwargs.pop(
                'hypervisor_id', 'd010ef1f-dc19-4982-9383-087498bfde03'
            ),
            'hypervisor_hostname': hostname,
            'hypervisor_type': kwargs.pop('hypervisor_type', 'QEMU'),
            'state': kwargs.pop('state', 'up'),
            'status': kwargs.pop('status', 'enabled'),
            'vcpus': kwargs.pop('vcpus', 16),
            'vcpus_used': kwargs.pop('vcpus_used', 4),
            'memory_mb': kwargs.pop('memory_mb', 32768),
            'memory_mb_used': kwargs.pop('memory_mb_used', 8192),
            'local_gb': kwargs.pop('local_gb', 500),
            'local_gb_used': kwargs.pop('local_gb_used', 100),
            'service': kwargs.pop('service', {'host': hostname, 'id': 1}),
            'servers': kwargs.pop('servers', None),
        }
        hypervisor_info.update(kwargs)
        return hypervisors.Hypervisor(
            hypervisors.HypervisorManager, info=hypervisor_info)

    def create_nova_flavor(self, **kwargs):
        """Create a real novaclient Flavor object.

        :param kwargs: additional flavor attributes
        :returns: novaclient.v2.flavors.Flavor object
        """
        flavor_info = {
            'id': kwargs.pop('id', 'flavor_id'),
            'name': kwargs.pop('name', 'flavor_name'),
            'vcpus': kwargs.pop('vcpus', 2),
            'ram': kwargs.pop('ram', 2048),
            'disk': kwargs.pop('disk', 20),
            'OS-FLV-EXT-DATA:ephemeral': kwargs.pop('ephemeral', 0),
            'swap': kwargs.pop('swap', ''),
            'os-flavor-access:is_public': kwargs.pop('is_public', True),
        }
        flavor_info.update(kwargs)
        return flavors.Flavor(flavors.FlavorManager, info=flavor_info)

    def create_nova_aggregate(self, **kwargs):
        """Create a real novaclient Aggregate object.

        :param kwargs: additional aggregate attributes
        :returns: novaclient.v2.aggregates.Aggregate object
        """

        aggregate_info = {
            'id': kwargs.pop('id', 'aggregate_id'),
            'name': kwargs.pop('name', 'aggregate_name'),
            'availability_zone': kwargs.pop('availability_zone', None),
            'hosts': kwargs.pop('hosts', []),
            'metadata': kwargs.pop('metadata', {}),
        }
        aggregate_info.update(kwargs)
        return aggregates.Aggregate(
            aggregates.AggregateManager, info=aggregate_info)

    def create_nova_service(self, **kwargs):
        """Create a real novaclient Service object.

        :param kwargs: additional service attributes
        :returns: novaclient.v2.services.Service object
        """

        service_info = {
            'id': kwargs.pop('id', 'd010ef1f-dc19-4982-9383-087498bfde03'),
            'binary': kwargs.pop('binary', 'nova-compute'),
            'host': kwargs.pop('host', 'compute-1'),
            'zone': kwargs.pop('zone', 'nova'),
            'status': kwargs.pop('status', 'enabled'),
            'state': kwargs.pop('state', 'up'),
            'updated_at': kwargs.pop('updated_at', '2026-01-09T12:00:00Z'),
            'disabled_reason': kwargs.pop('disabled_reason', None),
        }
        service_info.update(kwargs)
        return services.Service(services.ServiceManager, info=service_info)

    def create_nova_migration(self, migration_id, **kwargs):
        """Create a real novaclient ServerMigration object.

        :param migration_id: migration ID
        :param kwargs: additional migration attributes
        :returns: novaclient.v2.server_migrations.ServerMigration object
        """

        migration_info = {
            'id': migration_id,
        }
        migration_info.update(kwargs)
        return server_migrations.ServerMigration(
            server_migrations.ServerMigrationsManager, info=migration_info)
