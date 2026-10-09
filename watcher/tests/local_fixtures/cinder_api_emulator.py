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

"""Minimal Cinder v3 API emulator for functional tests.

Serves a subset of the Cinder v3 Block Storage API backed by in-memory
data derived from ``StorageTopology`` dicts.  Routes and payload shapes
match what openstacksdk's ``block_storage`` proxy (used by
``CinderHelper``) sends, including the ``all_tenants`` query-parameter
alias used by the SDK's ``all_projects`` keyword.

Supported endpoints (those used by watcher's collector, strategies,
and actions):

    GET  /os-services               (list services, filterable by binary)
    GET  /scheduler-stats/get_pools (list pools with capabilities)
    GET  /volumes/detail            (list volumes with details)
    GET  /volumes/<id>              (get single volume)
    POST /volumes/<id>/action       (os-migrate_volume, os-retype)
    GET  /types                     (list volume types)
    GET  /types/<id>                (get single volume type)
    GET  /snapshots/detail          (list snapshots with details)
    GET  /                          (root / version discovery)
"""

from xml.etree import ElementTree

from oslo_serialization import jsonutils
from pecan import abort
from pecan import expose
from pecan import request
from pecan import response
from pecan import rest

from watcher.tests.functional import topology as topo_mod
from watcher.tests.local_fixtures import base_emulator


def _backend_from_pool_name(name):
    """Extract the backend name segment from a ``host@backend#pool`` name."""
    try:
        return name.split('@')[1].split('#')[0]
    except IndexError:
        return ''


def _volume_id_from_xml(element):
    """Return volume/snapshot id from ``id`` or ``uuid`` XML attribute."""
    return element.attrib.get('id') or element.attrib.get('uuid')


class _ServicesController(rest.RestController):
    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def get_all(self):
        binary = request.params.get('binary')
        services = list(self._emulator.services.values())
        if binary:
            services = [s for s in services if s['binary'] == binary]
        return {'services': services}


class _SchedulerStatsController:
    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def get_pools(self):
        return {'pools': list(self._emulator.pools.values())}


class _VolumeActionController(rest.RestController):
    def __init__(self, emulator, volume_id):
        self._emulator = emulator
        self._volume_id = volume_id

    @expose('json')
    def post(self):
        vol = self._emulator.volumes.get(self._volume_id)
        if vol is None:
            abort(404, detail='Volume %s not found' % self._volume_id)

        body = request.json

        if 'os-migrate_volume' in body:
            dest = body['os-migrate_volume'].get('host')
            if dest:
                vol['os-vol-host-attr:host'] = dest
            vol['os-vol-mig-status-attr:migstat'] = 'success'
            response.status = 202
            return ''

        if 'os-retype' in body:
            new_type = body['os-retype'].get('new_type')
            if new_type:
                vol['volume_type'] = new_type
            response.status = 202
            return ''

        abort(400, detail='Unknown action')


class _VolumeController(rest.RestController):
    def __init__(self, emulator, volume_id):
        self._emulator = emulator
        self._volume_id = volume_id
        self.action = _VolumeActionController(emulator, volume_id)

    @expose('json')
    def get(self):
        vol = self._emulator.volumes.get(self._volume_id)
        if vol is None:
            abort(404, detail='Volume %s not found' % self._volume_id)
        return {'volume': vol}


class _VolumesController(rest.RestController):
    _custom_actions = {'detail': ['GET']}

    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def detail(self):
        volumes = list(self._emulator.volumes.values())
        return {'volumes': volumes}

    @expose()
    def _lookup(self, volume_id, *remainder):
        if volume_id == 'detail':
            return
        return _VolumeController(self._emulator, volume_id), remainder


class _TypesController(rest.RestController):
    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def get_all(self):
        return {'volume_types': list(self._emulator.volume_types.values())}

    @expose('json')
    def get_one(self, type_id):
        vtype = self._emulator.volume_types.get(type_id)
        if vtype is None:
            abort(404, detail='Volume type %s not found' % type_id)
        return {'volume_type': vtype}


class _SnapshotsController(rest.RestController):
    _custom_actions = {'detail': ['GET']}

    def __init__(self, emulator):
        self._emulator = emulator

    @expose('json')
    def detail(self):
        return {'snapshots': list(self._emulator.snapshots.values())}


class _CinderRootController:
    def __init__(self, emulator):
        self._emulator = emulator
        self.volumes = _VolumesController(emulator)
        self.types = _TypesController(emulator)

    @expose()
    def _lookup(self, segment, *remainder):
        controllers = {
            'os-services': _ServicesController,
            'snapshots': _SnapshotsController,
        }
        cls = controllers.get(segment)
        if cls:
            return cls(self._emulator), remainder
        if segment == 'scheduler-stats':
            return _SchedulerStatsController(self._emulator), remainder

    @expose('json')
    def index(self):
        return {
            'versions': [
                {
                    'id': 'v3.0',
                    'status': 'CURRENT',
                    'min_version': '3.0',
                    'version': '3.70',
                    'links': [{'rel': 'self', 'href': '/'}],
                }
            ]
        }


class CinderAPIEmulator(base_emulator.BaseAPIEmulator):
    """In-memory Cinder v3 API emulator.

    Manages storage cluster state (storage services, pools, volume
    types, volumes, snapshots) and exposes a Pecan WSGI app.

    Topology can be set up programmatically via ``load_topology()``
    from a ``StorageTopology`` object, or from XML/JSON model files via
    ``load_model()`` / ``load_from_xml()`` / ``load_from_json()``.

    Example (in tests)::

        from watcher.tests.functional import topology

        emulator = CinderAPIEmulator()
        emulator.load_topology(
            topology.StorageTopology()
            .add_storage_node('storage-1@backend1')
            .add_pool('storage-1@backend1#pool1')
        )
        wsgi_app = emulator.app
    """

    def _init_stores(self):
        self.services = {}
        self.pools = {}
        self.volume_types = {}
        self.volumes = {}
        self.snapshots = {}

    def _make_root_controller(self):
        return _CinderRootController(self)

    # Topology loading

    def load_topology(self, topology=None):
        """Load storage topology from a ``StorageTopology`` object.

        :param topology: A ``StorageTopology`` instance containing
            storage_nodes, pools, volume_types, volumes, and
            snapshots.
        """
        self.reset()
        if topology is None:
            topology = topo_mod.StorageTopology()
        storage_nodes = topo_mod.normalize(topology.storage_nodes)
        pools = topo_mod.normalize(topology.pools)
        volume_types = topo_mod.normalize(topology.volume_types)
        volumes = topo_mod.normalize(topology.volumes)
        snapshots = topo_mod.normalize(topology.snapshots)

        for node_def in storage_nodes or []:
            host = node_def['host']
            self.services[host] = {
                'host': host,
                'zone': node_def.get('zone', 'nova'),
                'status': node_def.get('status', 'enabled'),
                'state': node_def.get('state', 'up'),
                'binary': node_def.get('binary', 'cinder-volume'),
                'updated_at': '2024-01-01T00:00:00.000000',
                'disabled_reason': None,
            }

        for pool_def in pools or []:
            name = pool_def['name']
            opt_attributes = [
                'provisioned_capacity_gb',
                'allocated_capacity_gb',
                'total_volumes',
            ]
            backend = _backend_from_pool_name(name)
            self.pools[name] = {
                'name': name,
                'capabilities': {
                    'total_capacity_gb': pool_def.get('total_capacity_gb', 0),
                    'free_capacity_gb': pool_def.get('free_capacity_gb', 0),
                    'volume_backend_name': pool_def.get(
                        'volume_backend_name', backend
                    ),
                },
            }
            for opt_attribute in opt_attributes:
                value = pool_def.get(opt_attribute, None)
                if value is not None:
                    self.pools[name]['capabilities'][opt_attribute] = value

        for vtype_def in volume_types or []:
            vtype_id = vtype_def['id']
            self.volume_types[vtype_id] = {
                'id': vtype_id,
                'name': vtype_def['name'],
                'os-volume-type-access:is_public': vtype_def.get(
                    'is_public', True
                ),
                'extra_specs': vtype_def.get('extra_specs', {}),
                'description': vtype_def.get('description', None),
            }

        for vol_def in volumes or []:
            vol_id = vol_def['id']
            self.volumes[vol_id] = {
                'id': vol_id,
                'name': vol_def.get('name', ''),
                'size': vol_def.get('size', 0),
                'status': vol_def.get('status', 'available'),
                'volume_type': vol_def.get('volume_type', ''),
                'os-vol-host-attr:host': vol_def.get('host', ''),
                'os-vol-tenant-attr:tenant_id': vol_def.get('project_id', ''),
                'bootable': vol_def.get('bootable', False),
                'multiattach': vol_def.get('multiattach', False),
                'snapshot_id': vol_def.get('snapshot_id', None),
                'metadata': vol_def.get('metadata', {}),
                'attachments': vol_def.get('attachments', []),
                'availability_zone': vol_def.get('availability_zone', 'nova'),
                'created_at': vol_def.get(
                    'created_at', '2024-01-01T00:00:00.000000'
                ),
                'updated_at': None,
                'os-vol-mig-status-attr:name_id': None,
                'os-vol-mig-status-attr:migstat': None,
                'links': [],
            }

        for snap_def in snapshots or []:
            snap_id = snap_def['id']
            self.snapshots[snap_id] = {
                'id': snap_id,
                'name': snap_def.get('name', ''),
                'volume_id': snap_def.get('volume_id', ''),
                'status': snap_def.get('status', 'available'),
                'size': snap_def.get('size', 0),
                'created_at': '2024-01-01T00:00:00.000000',
                'metadata': snap_def.get('metadata', {}),
            }

    def load_from_xml(self, xml_path):
        """Load storage topology from a watcher storage scenario XML file.

        Format matches unit-test scenarios such as
        ``storage_scenario_1.xml``: ``StorageNode`` elements with nested
        ``Pool`` / ``Volume``, plus optional top-level ``Volume``,
        ``VolumeType``, and ``VolumeSnapshot`` elements.  When no
        ``VolumeType`` elements are present, types are synthesized from
        distinct ``volume_type`` attributes on volumes.
        """
        tree = ElementTree.parse(xml_path)
        root = tree.getroot()

        storage_nodes = []
        pools = []
        volumes = []
        volume_types = []
        snapshots = []

        for node in root.iter('StorageNode'):
            storage_nodes.append(
                base_emulator._parse_xml_element(node, topo_mod.StorageNode)
            )
            for pool_el in node.findall('Pool'):
                pools.append(
                    base_emulator._parse_xml_element(pool_el, topo_mod.Pool)
                )
                for vol_el in pool_el.findall('Volume'):
                    volumes.append(
                        base_emulator._parse_xml_element(
                            vol_el,
                            topo_mod.Volume,
                            id=_volume_id_from_xml(vol_el),
                        )
                    )

        # Orphan volumes (same idea as top-level Instance in compute XML)
        for vol_el in root.findall('Volume'):
            volumes.append(
                base_emulator._parse_xml_element(
                    vol_el, topo_mod.Volume, id=_volume_id_from_xml(vol_el)
                )
            )

        for vt_el in root.iter('VolumeType'):
            volume_types.append(
                base_emulator._parse_xml_element(vt_el, topo_mod.VolumeType)
            )

        for snap_el in root.iter('VolumeSnapshot'):
            snapshots.append(
                base_emulator._parse_xml_element(
                    snap_el,
                    topo_mod.VolumeSnapshot,
                    id=_volume_id_from_xml(snap_el),
                )
            )

        if not volume_types:
            names = {v.volume_type for v in volumes if v.volume_type}
            volume_types = [topo_mod.VolumeType(name=n) for n in sorted(names)]

        self.load_topology(
            topo_mod.StorageTopology(
                storage_nodes=storage_nodes,
                pools=pools,
                volume_types=volume_types,
                volumes=volumes,
                snapshots=snapshots,
            )
        )

    def load_from_json(self, json_path):
        """Load storage topology from a JSON file.

        Only fields defined on ``StorageNode``, ``Pool``,
        ``VolumeType``, ``Volume``, and ``VolumeSnapshot`` are used;
        unknown keys are silently ignored.  Missing fields use the
        dataclass defaults.
        """
        with open(json_path, 'rb') as f:
            data = jsonutils.load(f)
        self.load_topology(
            topo_mod.StorageTopology(
                storage_nodes=[
                    base_emulator._from_dict(topo_mod.StorageNode, d)
                    for d in data.get('storage_nodes', [])
                ],
                pools=[
                    base_emulator._from_dict(topo_mod.Pool, d)
                    for d in data.get('pools', [])
                ],
                volume_types=[
                    base_emulator._from_dict(topo_mod.VolumeType, d)
                    for d in data.get('volume_types', [])
                ],
                volumes=[
                    base_emulator._from_dict(topo_mod.Volume, d)
                    for d in data.get('volumes', [])
                ],
                snapshots=[
                    base_emulator._from_dict(topo_mod.VolumeSnapshot, d)
                    for d in data.get('snapshots', [])
                ],
            )
        )


def create_app(model_path=None, topology=None):
    """Factory to create a configured emulator and return it."""
    return base_emulator.create_app(
        CinderAPIEmulator, model_path=model_path, topology=topology
    )


def main():
    base_emulator.run_standalone(
        CinderAPIEmulator, 'Cinder API emulator', 8776
    )


if __name__ == '__main__':
    main()
