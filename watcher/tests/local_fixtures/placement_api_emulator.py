# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Minimal Placement API emulator for functional tests.

Serves a subset of the Placement API backed by in-memory data
derived from the same compute-node topology used by the Nova
emulator.

Supported endpoints (those used by watcher's collector):

    GET /resource_providers
    GET /resource_providers/<uuid>/inventories
    GET /resource_providers/<uuid>/traits
    GET /resource_providers/<uuid>/usages
    GET /allocations/<consumer_uuid>
    GET /  (root)
"""

import math

from pecan import abort
from pecan import expose
from pecan import request
from pecan import rest

from watcher.tests.functional import topology as topo_mod
from watcher.tests.local_fixtures import base_emulator


class _InventoriesController(rest.RestController):
    def __init__(self, emulator, rp_uuid):
        self._emulator = emulator
        self._rp_uuid = rp_uuid

    @expose('json')
    def get_all(self):
        inv = self._emulator.inventories.get(self._rp_uuid)
        if inv is None:
            abort(404)
        return {'inventories': inv, 'resource_provider_generation': 1}


class _TraitsController(rest.RestController):
    def __init__(self, emulator, rp_uuid):
        self._emulator = emulator
        self._rp_uuid = rp_uuid

    @expose('json')
    def get_all(self):
        t = self._emulator.traits.get(self._rp_uuid)
        if t is None:
            abort(404)
        return {'traits': t, 'resource_provider_generation': 1}


class _UsagesController(rest.RestController):
    def __init__(self, emulator, rp_uuid):
        self._emulator = emulator
        self._rp_uuid = rp_uuid

    @expose('json')
    def get_all(self):
        u = self._emulator.usages.get(self._rp_uuid)
        if u is None:
            abort(404)
        return {'usages': u, 'resource_provider_generation': 1}


class _SingleRPController:
    def __init__(self, emulator, rp_uuid):
        self.inventories = _InventoriesController(emulator, rp_uuid)
        self.traits = _TraitsController(emulator, rp_uuid)
        self.usages = _UsagesController(emulator, rp_uuid)


class _ResourceProvidersController(rest.RestController):
    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def get_all(self):
        name = request.params.get('name')
        rps = list(self._emulator.resource_providers.values())
        if name:
            rps = [rp for rp in rps if rp['name'] == name]
        return {'resource_providers': rps}

    @expose()
    def _lookup(self, rp_uuid, *remainder):
        return _SingleRPController(self._emulator, rp_uuid), remainder


class _AllocationsController(rest.RestController):
    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def get_one(self, consumer_uuid):
        allocs = self._emulator.allocations.get(consumer_uuid, {})
        return {'allocations': allocs, 'project_id': '', 'user_id': ''}


class _PlacementRootController:
    def __init__(self, emulator):
        self.resource_providers = _ResourceProvidersController(emulator)
        self.allocations = _AllocationsController(emulator)

    @expose('json')
    def index(self):
        return {
            'versions': [
                {
                    'id': 'v1.0',
                    'status': 'CURRENT',
                    'min_version': '1.0',
                    'max_version': '1.39',
                    'links': [{'rel': 'self', 'href': '/'}],
                }
            ]
        }


class PlacementAPIEmulator(base_emulator.BaseAPIEmulator):
    """In-memory Placement API emulator.

    Provides resource provider inventories, traits, usages, and
    allocations derived from compute node topology.

    Topology is loaded from the same ``ComputeTopology`` objects
    that the Nova emulator uses.
    """

    def _init_stores(self):
        self.resource_providers = {}
        self.inventories = {}
        self.usages = {}
        self.traits = {}
        self.allocations = {}

    def _make_root_controller(self):
        return _PlacementRootController(self)

    # Topology loading

    def load_topology(self, topology=None):
        """Build placement data from a ComputeTopology object.

        :param topology: A ComputeTopology instance. The aggregates
            field is ignored (placement doesn't use them directly).
        """
        self.reset()
        if topology is None:
            topology = topo_mod.ComputeTopology()
        compute_nodes = topo_mod.normalize(topology.compute_nodes)
        instances = topo_mod.normalize(topology.instances)
        nodes_by_host = {}

        for node_def in compute_nodes or []:
            hostname = node_def['hostname']
            rp_uuid = node_def.get('uuid', hostname)

            self.resource_providers[rp_uuid] = {
                'uuid': rp_uuid,
                'name': hostname,
                'generation': 1,
                'links': [],
            }

            vcpus = int(node_def['vcpus'])
            memory = int(node_def['memory'])
            disk = int(node_def['disk'])

            vcpu_ratio = float(node_def.get('vcpu_ratio', 1.0))
            memory_ratio = float(node_def.get('memory_ratio', 1.0))
            disk_ratio = float(node_def.get('disk_ratio', 1.0))

            self.inventories[rp_uuid] = {
                'VCPU': {
                    'total': vcpus,
                    'reserved': int(node_def.get('vcpu_reserved', 0)),
                    'min_unit': 1,
                    'max_unit': vcpus,
                    'step_size': 1,
                    'allocation_ratio': vcpu_ratio,
                },
                'MEMORY_MB': {
                    'total': memory,
                    'reserved': int(node_def.get('memory_mb_reserved', 0)),
                    'min_unit': 1,
                    'max_unit': memory,
                    'step_size': 1,
                    'allocation_ratio': memory_ratio,
                },
                'DISK_GB': {
                    'total': disk,
                    'reserved': int(node_def.get('disk_gb_reserved', 0)),
                    'min_unit': 1,
                    'max_unit': disk,
                    'step_size': 1,
                    'allocation_ratio': disk_ratio,
                },
            }

            self.usages[rp_uuid] = {'VCPU': 0, 'MEMORY_MB': 0, 'DISK_GB': 0}

            self.traits[rp_uuid] = node_def.get('traits', [])
            nodes_by_host[hostname] = rp_uuid

        for inst_def in instances or []:
            hostname = inst_def['host']
            rp_uuid = nodes_by_host.get(hostname)
            if not rp_uuid:
                continue

            vcpus = int(inst_def['vcpus'])
            ram = int(inst_def['memory'])
            bfv = inst_def.get('bfv', False)
            disk = 0 if bfv else int(inst_def['disk'])
            ephemeral = int(inst_def.get('ephemeral', 0))
            swap_mb = int(inst_def.get('swap', 0))
            swap_gb = math.ceil(swap_mb / 1024) if swap_mb else 0
            disk_gb = disk + ephemeral + swap_gb

            self.usages[rp_uuid]['VCPU'] += vcpus
            self.usages[rp_uuid]['MEMORY_MB'] += ram
            self.usages[rp_uuid]['DISK_GB'] += disk_gb

            consumer_uuid = inst_def['uuid']
            self.allocations[consumer_uuid] = {
                rp_uuid: {
                    'resources': {
                        'VCPU': vcpus,
                        'MEMORY_MB': ram,
                        'DISK_GB': disk_gb,
                    }
                }
            }


def create_app(model_path=None, topology=None):
    """Factory to create a configured emulator."""
    return base_emulator.create_app(
        PlacementAPIEmulator, model_path=model_path, topology=topology
    )


def main():
    base_emulator.run_standalone(
        PlacementAPIEmulator, 'Placement API emulator', 8778
    )


if __name__ == '__main__':
    main()
