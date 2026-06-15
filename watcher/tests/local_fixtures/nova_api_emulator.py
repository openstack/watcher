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

"""Minimal Nova v2.1 API emulator for functional tests.

Serves a subset of the Nova v2.1 API backed by in-memory data.
Topology (compute nodes and instances) can be loaded from:

  - Python dicts passed directly from test code
  - XML model files (same format as watcher unit-test scenarios)
  - JSON topology files

The emulator can run:

  - In-process via wsgi-intercept (for functional tests)
  - Standalone via dev server (for manual testing / debugging)

Supported endpoints (those used by watcher's collector and actions):

  Nova compute:
    GET  /v2.1/servers/detail
    GET  /v2.1/servers/<id>
    POST /v2.1/servers/<id>/action  (os-migrateLive, migrate, os-stop)
    GET  /v2.1/os-hypervisors/detail
    GET  /v2.1/os-hypervisors/<id>
    GET  /v2.1/os-services
    PUT  /v2.1/os-services/<id>
    GET  /v2.1/os-aggregates
    GET  /v2.1/os-aggregates/<id>
    GET  /v2.1/  (version discovery)
    GET  /       (root version listing)
"""

import copy
import hashlib
import uuid

from pecan import abort
from pecan import expose
from pecan import request
from pecan import response
from pecan import rest

from watcher.tests.functional import topology as topo_mod
from watcher.tests.local_fixtures import base_emulator


def _flavor_id(vcpus, ram, disk):
    """Deterministic flavor id derived from resource dimensions."""
    key = f"{vcpus}-{ram}-{disk}"
    return hashlib.md5(key.encode()).hexdigest()[:8]


def _deterministic_uuid(seed):
    """Reproducible UUID5 so service IDs stay stable across restarts."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


class _ActionController(rest.RestController):
    def __init__(self, emulator, server_id):
        self._emulator = emulator
        self._server_id = server_id

    @expose('json')
    def post(self):
        srv = self._emulator.servers.get(self._server_id)
        if srv is None:
            abort(404, detail='Server %s not found' % self._server_id)

        body = request.json

        if 'os-migrateLive' in body:
            dest = body['os-migrateLive'].get('host')
            if dest:
                self._emulator._move_server(self._server_id, dest)
            else:
                other_hosts = [
                    h['hypervisor_hostname']
                    for h in self._emulator.hypervisors.values()
                    if (
                        h['hypervisor_hostname'] != srv['OS-EXT-SRV-ATTR:host']
                    )
                ]
                if other_hosts:
                    self._emulator._move_server(
                        self._server_id, other_hosts[0]
                    )
            response.status = 202
            return ''

        if 'migrate' in body:
            dest = None
            if isinstance(body['migrate'], dict):
                dest = body['migrate'].get('host')
            if dest:
                self._emulator._move_server(self._server_id, dest)
                srv['status'] = 'VERIFY_RESIZE'
            else:
                other_hosts = [
                    h['hypervisor_hostname']
                    for h in self._emulator.hypervisors.values()
                    if (
                        h['hypervisor_hostname'] != srv['OS-EXT-SRV-ATTR:host']
                    )
                ]
                if other_hosts:
                    self._emulator._move_server(
                        self._server_id, other_hosts[0]
                    )
                srv['status'] = 'VERIFY_RESIZE'
            response.status = 202
            return ''

        if 'confirmResize' in body:
            srv['status'] = 'ACTIVE'
            response.status = 204
            return ''

        if 'os-stop' in body:
            srv['status'] = 'SHUTOFF'
            srv['OS-EXT-STS:vm_state'] = 'stopped'
            srv['OS-EXT-STS:power_state'] = 4
            response.status = 202
            return ''

        if 'os-start' in body:
            srv['status'] = 'ACTIVE'
            srv['OS-EXT-STS:vm_state'] = 'active'
            srv['OS-EXT-STS:power_state'] = 1
            response.status = 202
            return ''

        abort(400, detail='Unknown action')


class _MigrationsController(rest.RestController):
    def __init__(self, emulator, server_id):
        self._emulator = emulator
        self._server_id = server_id

    @expose('json')
    def get_all(self):
        srv = self._emulator.servers.get(self._server_id)
        if srv is None:
            abort(404, detail='Server %s not found' % self._server_id)
        return {'migrations': []}


class _ServerController(rest.RestController):
    def __init__(self, emulator, server_id):
        self._emulator = emulator
        self._server_id = server_id
        self.action = _ActionController(emulator, server_id)
        self.migrations = _MigrationsController(emulator, server_id)

    @expose('json')
    def get(self):
        srv = self._emulator.servers.get(self._server_id)
        if srv is None:
            abort(404, detail='Server %s not found' % self._server_id)
        return {'server': srv}


class _ServersController(rest.RestController):
    _custom_actions = {'detail': ['GET']}

    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def detail(self):
        limit = request.params.get('limit', None)
        if limit is not None:
            limit = int(limit)
        marker = request.params.get('marker')
        host = request.params.get('host')
        all_servers = list(self._emulator.servers.values())
        if host:
            all_servers = [
                s for s in all_servers if s['OS-EXT-SRV-ATTR:host'] == host
            ]
        page, has_more = NovaAPIEmulator._paginate(all_servers, limit, marker)
        body = {'servers': page}
        if has_more:
            last_id = page[-1]['id']
            body['servers_links'] = [
                {
                    'rel': 'next',
                    'href': '/v2.1/servers/detail?limit=%s&marker=%s'
                    % (limit, last_id),
                }
            ]
        return body

    @expose()
    def _lookup(self, server_id, *remainder):
        if server_id == 'detail':
            return
        return _ServerController(self._emulator, server_id), remainder


class _HypervisorsController(rest.RestController):
    _custom_actions = {'detail': ['GET']}

    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def detail(self):
        pattern = request.params.get('hypervisor_hostname_pattern')
        with_servers = request.params.get('with_servers')
        hyps = list(self._emulator.hypervisors.values())
        if pattern:
            hyps = [h for h in hyps if h['hypervisor_hostname'] == pattern]
        result = []
        for h in hyps:
            entry = copy.deepcopy(h)
            if not with_servers:
                entry.pop('servers', None)
            result.append(entry)
        return {'hypervisors': result}

    @expose('json')
    def get_one(self, hyp_id):
        hyp = self._emulator.hypervisors.get(hyp_id)
        if hyp is None:
            abort(404)
        return {'hypervisor': hyp}


class _ServicesController(rest.RestController):
    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def get_all(self):
        host = request.params.get('host')
        binary = request.params.get('binary')
        svcs = list(self._emulator.services.values())
        if host:
            svcs = [s for s in svcs if s['host'] == host]
        if binary:
            svcs = [s for s in svcs if s['binary'] == binary]
        return {'services': svcs}

    @expose('json')
    def put(self, service_id):
        svc = self._emulator.services.get(service_id)
        if svc is None:
            abort(404)
        body = request.json
        if 'status' in body:
            svc['status'] = body['status']
            hyp = self._emulator._find_hypervisor_by_hostname(svc['host'])
            if hyp:
                hyp['status'] = body['status']
                hyp['service']['disabled_reason'] = body.get('disabled_reason')
        if 'disabled_reason' in body:
            svc['disabled_reason'] = body['disabled_reason']
        return {'service': svc}


class _FlavorsController(rest.RestController):
    _custom_actions = {'detail': ['GET']}

    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def detail(self):
        return {'flavors': list(self._emulator.flavors.values())}

    @expose('json')
    def get_all(self):
        return {'flavors': list(self._emulator.flavors.values())}

    @expose('json')
    def get_one(self, flavor_id):
        flv = self._emulator.flavors.get(flavor_id)
        if flv is None:
            abort(404, detail='Flavor %s not found' % flavor_id)
        return {'flavor': flv}


class _AggregatesController(rest.RestController):
    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def get_all(self):
        return {'aggregates': list(self._emulator.aggregates.values())}

    @expose('json')
    def get_one(self, agg_id):
        agg = self._emulator.aggregates.get(int(agg_id))
        if agg is None:
            abort(404)
        return {'aggregate': agg}


class _V21Controller:
    def __init__(self, emulator):
        self._emulator = emulator
        self.servers = _ServersController(emulator)
        self.flavors = _FlavorsController(emulator)

    @expose()
    def _lookup(self, segment, *remainder):
        controllers = {
            'os-hypervisors': _HypervisorsController,
            'os-services': _ServicesController,
            'os-aggregates': _AggregatesController,
        }
        cls = controllers.get(segment)
        if cls:
            return cls(self._emulator), remainder

    @expose('json')
    def index(self):
        base = request.host_url.rstrip('/')
        return {
            'version': {
                'id': 'v2.1',
                'links': [{'href': '%s/v2.1/' % base, 'rel': 'self'}],
                'status': 'CURRENT',
                'version': '2.103',
                'min_version': '2.1',
                'updated': '2013-07-23T11:33:21Z',
            }
        }


class _NovaRootController:
    def __init__(self, emulator):
        self._emulator = emulator

    @expose()
    def _lookup(self, segment, *remainder):
        if segment == 'v2.1':
            return _V21Controller(self._emulator), remainder

    @expose('json')
    def index(self):
        base = request.host_url.rstrip('/')
        return {
            'versions': [
                {
                    'id': 'v2.1',
                    'status': 'CURRENT',
                    'links': [{'rel': 'self', 'href': '%s/v2.1/' % base}],
                }
            ]
        }


class NovaAPIEmulator(base_emulator.BaseAPIEmulator):
    """In-memory Nova API emulator.

    Manages cluster state (servers, hypervisors, services, flavors,
    aggregates) and exposes a Pecan WSGI app.

    Topology can be set up programmatically via ``load_topology()``
    or from XML/JSON model files via ``load_model()``.

    Example (in tests)::

        from watcher.tests.functional import topology

        emulator = NovaAPIEmulator()
        emulator.load_topology(
            topology.ComputeTopology()
            .add_computes(count=2)
            .add_instances(computes=['compute-1'], count=1, vcpus=2)
        )
        wsgi_app = emulator.app
    """

    def _init_stores(self):
        self.servers = {}
        self.hypervisors = {}
        self.services = {}
        self.flavors = {}
        self.aggregates = {}

    def _make_root_controller(self):
        return _NovaRootController(self)

    # Topology loading

    def load_topology(self, topology=None):
        """Load cluster topology from a ComputeTopology object.

        :param topology: A ComputeTopology instance containing
            compute_nodes, instances, and aggregates.
        """
        self.reset()
        if topology is None:
            topology = topo_mod.ComputeTopology()
        compute_nodes = topo_mod.normalize(topology.compute_nodes)
        instances = topo_mod.normalize(topology.instances)
        aggregates = topo_mod.normalize(topology.aggregates)
        nodes_by_host = {}

        for node_def in compute_nodes or []:
            hostname = node_def['hostname']
            node_uuid = node_def.get('uuid', _deterministic_uuid(hostname))
            service_uuid = _deterministic_uuid(f"service-{hostname}")

            state = node_def.get('state', 'up')
            status = node_def.get('status', 'enabled')
            disabled_reason = node_def.get('disabled_reason', None)

            service = {
                'id': service_uuid,
                'binary': 'nova-compute',
                'host': hostname,
                'zone': node_def.get('availability_zone', 'nova'),
                'status': status,
                'state': state,
                'disabled_reason': disabled_reason,
            }
            self.services[service_uuid] = service

            hypervisor = {
                'id': node_uuid,
                'hypervisor_hostname': hostname,
                'hypervisor_type': 'libvirt',
                'state': state,
                'status': status,
                'vcpus': int(node_def['vcpus']),
                'vcpus_used': 0,
                'memory_size': int(node_def['memory']),
                'memory_mb': int(node_def['memory']),
                'memory_used': 0,
                'memory_mb_used': 0,
                'local_gb': int(node_def['disk']),
                'local_gb_used': 0,
                'running_vms': 0,
                'servers': [],
                'service': {
                    'id': service_uuid,
                    'host': hostname,
                    'disabled_reason': disabled_reason,
                },
            }
            self.hypervisors[node_uuid] = hypervisor
            nodes_by_host[hostname] = hypervisor

        for inst_def in instances or []:
            inst_uuid = inst_def['uuid']
            hostname = inst_def['host']
            hyp_hostname = inst_def.get('hypervisor_hostname', hostname)
            vcpus = int(inst_def['vcpus'])
            ram = int(inst_def['memory'])
            disk = int(inst_def['disk'])
            ephemeral = int(inst_def.get('ephemeral', 0))
            swap = int(inst_def.get('swap', 0))
            state = inst_def.get('state', 'active')
            created = inst_def.get('created', '2025-01-01T00:00:00Z')
            fid = _flavor_id(vcpus, ram, disk)

            if fid not in self.flavors:
                self.flavors[fid] = {
                    'id': fid,
                    'name': 'flavor-%s' % fid,
                    'vcpus': vcpus,
                    'ram': ram,
                    'disk': disk,
                    'OS-FLV-EXT-DATA:ephemeral': ephemeral,
                    'swap': swap,
                    'os-flavor-access:is_public': True,
                    'extra_specs': {},
                }

            status = 'ACTIVE' if state == 'active' else state.upper()
            bfv = inst_def.get('bfv', False)
            image = (
                ''
                if bfv
                else {'id': _deterministic_uuid(f'image-{inst_uuid}')}
            )

            server = {
                'id': inst_uuid,
                'name': inst_def.get('name', f'instance-{inst_uuid[:8]}'),
                'status': status,
                'tenant_id': inst_def.get('project_id', ''),
                'user_id': '',
                'metadata': inst_def.get('metadata', {}),
                'hostId': hostname,
                'image': image,
                'flavor': {
                    'id': fid,
                    'vcpus': vcpus,
                    'ram': ram,
                    'disk': disk,
                    'ephemeral': ephemeral,
                    'swap': swap,
                    'extra_specs': {},
                },
                'created': created,
                'updated': created,
                'addresses': {},
                'accessIPv4': '',
                'accessIPv6': '',
                'links': [],
                'OS-DCF:diskConfig': 'AUTO',
                'progress': 0,
                'OS-EXT-STS:power_state': 1 if state == 'active' else 0,
                'OS-EXT-STS:vm_state': state,
                'OS-EXT-STS:task_state': None,
                'OS-EXT-SRV-ATTR:host': hostname,
                'OS-EXT-SRV-ATTR:instance_name': inst_def.get(
                    'name', f'instance-{inst_uuid[:8]}'
                ),
                'OS-EXT-SRV-ATTR:hypervisor_hostname': hyp_hostname,
                'OS-EXT-AZ:availability_zone': inst_def.get(
                    'availability_zone', 'nova'
                ),
                'config_drive': '',
                'key_name': None,
                'security_groups': [{'name': 'default'}],
                'os-extended-volumes:volumes_attached': [],
                'locked': inst_def.get('locked', False),
                'pinned_availability_zone': inst_def.get('pinned_az', None),
            }
            self.servers[inst_uuid] = server

            if hostname in nodes_by_host:
                hyp = nodes_by_host[hostname]
                hyp['vcpus_used'] += vcpus
                hyp['memory_used'] += ram
                hyp['memory_mb_used'] += ram
                hyp['local_gb_used'] += disk
                hyp['running_vms'] += 1
                hyp['servers'].append(
                    {'uuid': inst_uuid, 'name': server['name']}
                )

        for agg_def in aggregates or []:
            self.aggregates[agg_def['id']] = {
                'id': agg_def['id'],
                'name': agg_def['name'],
                'hosts': list(agg_def.get('hosts', [])),
                'metadata': agg_def.get('metadata', {}),
                'availability_zone': agg_def.get('availability_zone'),
            }

    # Helper methods

    def _get_servers_on_host(self, hostname):
        return [
            s
            for s in self.servers.values()
            if s['OS-EXT-SRV-ATTR:host'] == hostname
        ]

    def _find_hypervisor_by_hostname(self, hostname):
        for hyp in self.hypervisors.values():
            if hyp['hypervisor_hostname'] == hostname:
                return hyp
        return None

    def _find_service_by_hostname(self, hostname):
        for svc in self.services.values():
            if svc['host'] == hostname:
                return svc
        return None

    def _move_server(self, server_id, dest_hostname):
        """Move a server to a new host in the emulator state."""
        server = self.servers.get(server_id)
        if not server:
            return
        old_host = server['OS-EXT-SRV-ATTR:host']
        server['OS-EXT-SRV-ATTR:host'] = dest_hostname
        server['OS-EXT-SRV-ATTR:hypervisor_hostname'] = dest_hostname
        server['hostId'] = dest_hostname

        vcpus = server['flavor']['vcpus']
        ram = server['flavor']['ram']
        disk = server['flavor']['disk']

        old_hyp = self._find_hypervisor_by_hostname(old_host)
        if old_hyp:
            old_hyp['vcpus_used'] = max(0, old_hyp['vcpus_used'] - vcpus)
            old_hyp['memory_used'] = max(0, old_hyp['memory_used'] - ram)
            old_hyp['memory_mb_used'] = max(0, old_hyp['memory_mb_used'] - ram)
            old_hyp['local_gb_used'] = max(0, old_hyp['local_gb_used'] - disk)
            old_hyp['running_vms'] = max(0, old_hyp['running_vms'] - 1)
            old_hyp['servers'] = [
                s for s in old_hyp['servers'] if s['uuid'] != server_id
            ]

        new_hyp = self._find_hypervisor_by_hostname(dest_hostname)
        if new_hyp:
            new_hyp['vcpus_used'] += vcpus
            new_hyp['memory_used'] += ram
            new_hyp['memory_mb_used'] += ram
            new_hyp['local_gb_used'] += disk
            new_hyp['running_vms'] += 1
            new_hyp['servers'].append(
                {'uuid': server_id, 'name': server['name']}
            )

    @staticmethod
    def _paginate(items, limit, marker):
        if marker:
            found = False
            filtered = []
            for item in items:
                if found:
                    filtered.append(item)
                if item['id'] == marker:
                    found = True
            items = filtered
        if limit and limit > 0 and limit < len(items):
            return items[:limit], True
        return items, False


def create_app(model_path=None, topology=None):
    """Factory to create a configured emulator and return it."""
    return base_emulator.create_app(
        NovaAPIEmulator, model_path=model_path, topology=topology
    )


def main():
    base_emulator.run_standalone(NovaAPIEmulator, 'Nova API emulator', 8774)


if __name__ == '__main__':
    main()
