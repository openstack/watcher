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

"""Functional tests for the Nova compute data model.

Validates that the cluster data model built from the emulated Nova and
Placement APIs contains the correct nodes, instances, resource
accounting, and scope filtering.

Tests use ``get_data_model()`` which calls the Decision Engine via RPC
and returns the unfiltered ``to_list()`` representation — the same
data the API would serve, but without frozen-field filtering.
"""

import math
import os

from watcher.tests.functional import base
from watcher.tests.functional import topology


# Topology

TOPOLOGY = topology.ComputeTopology(
    compute_nodes=[
        topology.ComputeNode(
            uuid='aaaa0001-0000-0000-0000-000000000001',
            hostname='compute-1',
            vcpus=64,
            memory=131072,
            disk=2000,
            vcpu_ratio=2.0,
            memory_ratio=1.5,
            vcpu_reserved=4,
            memory_mb_reserved=512,
            disk_gb_reserved=10,
        ),
        topology.ComputeNode(
            uuid='aaaa0002-0000-0000-0000-000000000002',
            hostname='compute-2',
            vcpus=32,
            memory=65536,
            disk=1000,
        ),
        topology.ComputeNode(
            uuid='aaaa0003-0000-0000-0000-000000000003',
            hostname='compute-3',
            status='disabled',
        ),
        topology.ComputeNode(
            uuid='aaaa0004-0000-0000-0000-000000000004',
            hostname='compute-empty',
        ),
    ],
    instances=[
        # compute-1: mix of regular, BFV, ephemeral, swap
        topology.Instance(
            uuid='bbbb0001-0000-0000-0000-000000000001',
            name='regular-vm',
            host='compute-1',
            memory=8192,
            disk=40,
            project_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        ),
        topology.Instance(
            uuid='bbbb0002-0000-0000-0000-000000000002',
            name='bfv-vm',
            host='compute-1',
            vcpus=2,
            disk=80,
            bfv=True,
            project_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        ),
        topology.Instance(
            uuid='bbbb0003-0000-0000-0000-000000000003',
            name='ephemeral-vm',
            host='compute-1',
            memory=16384,
            disk=20,
            ephemeral=50,
            project_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        ),
        topology.Instance(
            uuid='bbbb0004-0000-0000-0000-000000000004',
            name='swap-vm',
            host='compute-1',
            vcpus=2,
            disk=10,
            swap=512,
            project_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        ),
        topology.Instance(
            uuid='bbbb0005-0000-0000-0000-000000000005',
            name='full-vm',
            host='compute-1',
            vcpus=8,
            memory=32768,
            disk=100,
            ephemeral=200,
            swap=1789,
            project_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        ),
        topology.Instance(
            uuid='bbbb0006-0000-0000-0000-000000000006',
            name='bfv-with-ephemeral',
            host='compute-1',
            vcpus=2,
            memory=2048,
            disk=40,
            ephemeral=10,
            swap=352,
            bfv=True,
            project_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        ),
        # compute-2: paused and stopped instances
        topology.Instance(
            uuid='cccc0001-0000-0000-0000-000000000001',
            name='paused-vm',
            host='compute-2',
            memory=8192,
            disk=30,
            state='paused',
            project_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        ),
        topology.Instance(
            uuid='cccc0002-0000-0000-0000-000000000002',
            name='stopped-vm',
            host='compute-2',
            vcpus=2,
            state='stopped',
            project_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        ),
        # compute-3: disabled node with active instance
        topology.Instance(
            uuid='dddd0001-0000-0000-0000-000000000001',
            name='vm-on-disabled',
            host='compute-3',
            vcpus=2,
            project_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
        ),
        # compute-empty: no instances
    ],
    aggregates=[
        topology.Aggregate(
            id=1, name='prod', hosts=['compute-1', 'compute-2']
        ),
        topology.Aggregate(id=2, name='staging', hosts=['compute-3']),
    ],
)


# Helpers


def _nodes_from_model(model):
    """Extract unique node dicts from the to_list() output."""
    seen = set()
    nodes = []
    for entry in model:
        hostname = entry['node_hostname']
        if hostname not in seen:
            seen.add(hostname)
            nodes.append(
                {k: v for k, v in entry.items() if k.startswith('node_')}
            )
    return nodes


def _servers_from_model(model):
    """Extract server dicts from the to_list() output."""
    return [
        {k: v for k, v in entry.items() if k.startswith('server_')}
        for entry in model
        if 'server_uuid' in entry
    ]


def _find_server(model, uuid):
    """Find a single server entry by UUID."""
    for entry in model:
        if entry.get('server_uuid') == uuid:
            return entry
    return None


def _find_node(model, hostname):
    """Find a single node entry by hostname (first occurrence)."""
    for entry in model:
        if entry.get('node_hostname') == hostname:
            return entry
    return None


# Test class


class TestNovaModel(base.WatcherFunctionalTestCase):
    """Validate the compute data model returned via RPC."""

    COMPUTE_TOPOLOGY = TOPOLOGY

    def setUp(self):
        super().setUp()
        self.model = self.get_data_model()

    # Structure

    def test_node_count(self):
        """All four compute nodes are present in the model."""
        nodes = _nodes_from_model(self.model)
        hostnames = {n['node_hostname'] for n in nodes}
        self.assertEqual(
            {'compute-1', 'compute-2', 'compute-3', 'compute-empty'}, hostnames
        )

    def test_instance_count(self):
        """All nine instances are present in the model."""
        servers = _servers_from_model(self.model)
        self.assertEqual(9, len(servers))

    def test_empty_node_has_entry(self):
        """A node with no instances still appears in to_list output."""
        entry = _find_node(self.model, 'compute-empty')
        self.assertIsNotNone(entry)
        self.assertNotIn('server_uuid', entry)

    def test_instance_to_node_mapping(self):
        """Each instance is mapped to the correct compute node."""
        expected = {
            'bbbb0001-0000-0000-0000-000000000001': 'compute-1',
            'bbbb0002-0000-0000-0000-000000000002': 'compute-1',
            'bbbb0003-0000-0000-0000-000000000003': 'compute-1',
            'bbbb0004-0000-0000-0000-000000000004': 'compute-1',
            'bbbb0005-0000-0000-0000-000000000005': 'compute-1',
            'bbbb0006-0000-0000-0000-000000000006': 'compute-1',
            'cccc0001-0000-0000-0000-000000000001': 'compute-2',
            'cccc0002-0000-0000-0000-000000000002': 'compute-2',
            'dddd0001-0000-0000-0000-000000000001': 'compute-3',
        }
        for uuid, hostname in expected.items():
            entry = _find_server(self.model, uuid)
            self.assertIsNotNone(entry, 'Instance %s not found' % uuid)
            self.assertEqual(
                hostname,
                entry['node_hostname'],
                'Instance %s should be on %s' % (uuid, hostname),
            )

    # Node attributes

    def test_node_capacity(self):
        """Compute-1 node attributes match the topology definition."""
        entry = _find_node(self.model, 'compute-1')
        self.assertEqual(64, entry['node_vcpus'])
        self.assertEqual(131072, entry['node_memory'])
        self.assertEqual(2000, entry['node_disk'])

    def test_node_ratios(self):
        """Overcommit ratios are set for compute-1."""
        entry = _find_node(self.model, 'compute-1')
        self.assertEqual(2.0, entry['node_vcpu_ratio'])
        self.assertEqual(1.5, entry['node_memory_ratio'])
        self.assertEqual(1.0, entry['node_disk_ratio'])

    def test_node_default_ratios(self):
        """Nodes without explicit ratios default to 1.0."""
        entry = _find_node(self.model, 'compute-2')
        self.assertEqual(1.0, entry['node_vcpu_ratio'])
        self.assertEqual(1.0, entry['node_memory_ratio'])
        self.assertEqual(1.0, entry['node_disk_ratio'])

    def test_node_reserved_resources(self):
        """Reserved resources are set for compute-1."""
        entry = _find_node(self.model, 'compute-1')
        self.assertEqual(4, entry['node_vcpu_reserved'])
        self.assertEqual(512, entry['node_memory_mb_reserved'])
        self.assertEqual(10, entry['node_disk_gb_reserved'])

    def test_node_default_reserved(self):
        """Nodes without explicit reserved default to 0."""
        entry = _find_node(self.model, 'compute-2')
        self.assertEqual(0, entry['node_vcpu_reserved'])
        self.assertEqual(0, entry['node_memory_mb_reserved'])
        self.assertEqual(0, entry['node_disk_gb_reserved'])

    def test_node_state_and_status(self):
        """Node state and status reflect topology definition."""
        entry = _find_node(self.model, 'compute-3')
        self.assertEqual('up', entry['node_state'])
        self.assertEqual('disabled', entry['node_status'])

    # Instance states

    def test_active_instance_state(self):
        entry = _find_server(
            self.model, 'bbbb0001-0000-0000-0000-000000000001'
        )
        self.assertEqual('active', entry['server_state'])

    def test_paused_instance_state(self):
        entry = _find_server(
            self.model, 'cccc0001-0000-0000-0000-000000000001'
        )
        self.assertEqual('paused', entry['server_state'])

    def test_stopped_instance_state(self):
        entry = _find_server(
            self.model, 'cccc0002-0000-0000-0000-000000000002'
        )
        self.assertEqual('stopped', entry['server_state'])

    # Disk accounting: regular instances

    def test_disk_regular_instance(self):
        """Regular instance: disk = root_disk."""
        entry = _find_server(
            self.model, 'bbbb0001-0000-0000-0000-000000000001'
        )
        self.assertEqual(40, entry['server_disk'])

    def test_disk_with_ephemeral(self):
        """Instance with ephemeral: disk = root + ephemeral."""
        entry = _find_server(
            self.model, 'bbbb0003-0000-0000-0000-000000000003'
        )
        self.assertEqual(20 + 50, entry['server_disk'])

    def test_disk_with_swap(self):
        """Instance with swap: disk = root + ceil(swap_mb/1024)."""
        entry = _find_server(
            self.model, 'bbbb0004-0000-0000-0000-000000000004'
        )
        expected = 10 + math.ceil(512 / 1024)  # 10 + 1 = 11
        self.assertEqual(expected, entry['server_disk'])

    def test_disk_with_ephemeral_and_swap(self):
        """Instance with both ephemeral and swap."""
        entry = _find_server(
            self.model, 'bbbb0005-0000-0000-0000-000000000005'
        )
        # root=100 + ephemeral=200 + ceil(1789/1024)=2
        expected = 100 + 200 + math.ceil(1789 / 1024)
        self.assertEqual(expected, entry['server_disk'])

    # Disk accounting: BFV instances

    def test_disk_bfv_instance(self):
        """BFV instance: root disk is excluded, disk = 0."""
        entry = _find_server(
            self.model, 'bbbb0002-0000-0000-0000-000000000002'
        )
        self.assertEqual(0, entry['server_disk'])

    def test_disk_bfv_with_ephemeral_and_swap(self):
        """BFV instance with ephemeral and swap: root=0 but others count."""
        entry = _find_server(
            self.model, 'bbbb0006-0000-0000-0000-000000000006'
        )
        # root=0 (BFV) + ephemeral=10 + ceil(352/1024)=1
        expected = 0 + 10 + math.ceil(352 / 1024)
        self.assertEqual(expected, entry['server_disk'])

    # Resource fields

    def test_instance_vcpus(self):
        entry = _find_server(
            self.model, 'bbbb0005-0000-0000-0000-000000000005'
        )
        self.assertEqual(8, entry['server_vcpus'])

    def test_instance_memory(self):
        entry = _find_server(
            self.model, 'bbbb0005-0000-0000-0000-000000000005'
        )
        self.assertEqual(32768, entry['server_memory'])

    def test_instance_project(self):
        entry = _find_server(
            self.model, 'bbbb0001-0000-0000-0000-000000000001'
        )
        self.assertEqual(
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', entry['server_project_id']
        )

    # Model fields completeness

    def test_node_fields_present(self):
        """All expected node_* fields exist in the model."""
        entry = _find_node(self.model, 'compute-1')
        expected_fields = {
            'node_uuid',
            'node_hostname',
            'node_status',
            'node_state',
            'node_memory',
            'node_memory_mb_reserved',
            'node_disk',
            'node_disk_gb_reserved',
            'node_vcpus',
            'node_vcpu_reserved',
            'node_memory_ratio',
            'node_vcpu_ratio',
            'node_disk_ratio',
        }
        for field in expected_fields:
            self.assertIn(field, entry, 'Missing field: %s' % field)

    def test_server_fields_present(self):
        """All expected server_* fields exist in the model."""
        entry = _find_server(
            self.model, 'bbbb0001-0000-0000-0000-000000000001'
        )
        expected_fields = {
            'server_uuid',
            'server_name',
            'server_state',
            'server_memory',
            'server_disk',
            'server_vcpus',
            'server_metadata',
            'server_project_id',
            'server_watcher_exclude',
            'server_locked',
        }
        for field in expected_fields:
            self.assertIn(field, entry, 'Missing field: %s' % field)

    # Topology reload

    def test_reload_topology(self):
        """Reloading topology replaces the model completely."""
        new_topology = topology.ComputeTopology(
            compute_nodes=[
                topology.ComputeNode(
                    uuid='eeee0001-0000-0000-0000-000000000001',
                    hostname='new-host',
                    vcpus=8,
                    memory=16384,
                    disk=100,
                )
            ],
            instances=[
                topology.Instance(
                    uuid='ffff0001-0000-0000-0000-000000000001',
                    name='new-vm',
                    host='new-host',
                    vcpus=2,
                    memory=2048,
                    disk=10,
                    project_id='dddddddd-dddd-dddd-dddd-dddddddddddd',
                )
            ],
        )
        self.load_topology(new_topology)
        model = self.get_data_model()
        nodes = _nodes_from_model(model)
        servers = _servers_from_model(model)
        self.assertEqual(1, len(nodes))
        self.assertEqual('new-host', nodes[0]['node_hostname'])
        self.assertEqual(1, len(servers))
        self.assertEqual(
            'ffff0001-0000-0000-0000-000000000001', servers[0]['server_uuid']
        )


class TestNovaModelFromXML(base.WatcherFunctionalTestCase):
    """Validate loading topology from XML model files."""

    COMPUTE_TOPOLOGY = topology.ComputeTopology()

    XML_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '../unit/decision_engine/model/data/scenario_3_with_2_nodes.xml',
    )

    def setUp(self):
        super().setUp()
        fixture = self.env.nova_fixture
        fixture.nova_emulator.load_from_xml(self.XML_PATH)
        fixture.placement_emulator.load_from_xml(self.XML_PATH)
        fixture._invalidate_collector_model()
        self.model = self.get_data_model()

    def test_node_count(self):
        nodes = _nodes_from_model(self.model)
        self.assertEqual(2, len(nodes))

    def test_node_hostnames(self):
        hostnames = {e['node_hostname'] for e in self.model}
        self.assertEqual({'hostname_0', 'hostname_1'}, hostnames)

    def test_node_attributes(self):
        entry = _find_node(self.model, 'hostname_0')
        self.assertEqual(
            'fa69c544-906b-4a6a-a9c6-c1f7a8078c73', entry['node_uuid']
        )
        self.assertEqual(40, entry['node_vcpus'])
        self.assertEqual(132, entry['node_memory'])
        self.assertEqual(250, entry['node_disk'])
        self.assertEqual('enabled', entry['node_status'])
        self.assertEqual('up', entry['node_state'])

    def test_instance_count(self):
        servers = _servers_from_model(self.model)
        self.assertEqual(2, len(servers))

    def test_instance_mapping(self):
        entry = _find_server(
            self.model, '73b09e16-35b7-4922-804e-e8f5d9b740fc'
        )
        self.assertIsNotNone(entry)
        self.assertEqual('hostname_0', entry['node_hostname'])
        self.assertEqual(10, entry['server_vcpus'])
        self.assertEqual(2, entry['server_memory'])
        self.assertEqual(20, entry['server_disk'])

        entry = _find_server(
            self.model, 'a4cab39b-9828-413a-bf88-f76921bf1517'
        )
        self.assertIsNotNone(entry)
        self.assertEqual('hostname_1', entry['node_hostname'])

    def test_node_ratios_from_xml(self):
        entry = _find_node(self.model, 'hostname_0')
        self.assertEqual(1.0, entry['node_vcpu_ratio'])
        self.assertEqual(1.0, entry['node_memory_ratio'])
        self.assertEqual(1.0, entry['node_disk_ratio'])

    def test_node_reserved_from_xml(self):
        entry = _find_node(self.model, 'hostname_0')
        self.assertEqual(0, entry['node_vcpu_reserved'])
        self.assertEqual(0, entry['node_memory_mb_reserved'])
        self.assertEqual(0, entry['node_disk_gb_reserved'])


class TestNovaModelFromJSON(base.WatcherFunctionalTestCase):
    """Validate loading topology from JSON files."""

    COMPUTE_TOPOLOGY = topology.ComputeTopology()

    JSON_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '../local_fixtures/sample_topology.json',
    )

    def setUp(self):
        super().setUp()
        fixture = self.env.nova_fixture
        fixture.nova_emulator.load_from_json(self.JSON_PATH)
        fixture.placement_emulator.load_from_json(self.JSON_PATH)
        fixture._invalidate_collector_model()
        self.model = self.get_data_model()

    def test_node_count(self):
        nodes = _nodes_from_model(self.model)
        self.assertEqual(2, len(nodes))

    def test_node_hostnames(self):
        hostnames = {e['node_hostname'] for e in self.model}
        self.assertEqual({'compute-1', 'compute-2'}, hostnames)

    def test_node_attributes(self):
        entry = _find_node(self.model, 'compute-1')
        self.assertEqual(
            '73b09e16-35b7-4922-804e-e8f5d9b740fc', entry['node_uuid']
        )
        self.assertEqual(16, entry['node_vcpus'])
        self.assertEqual(32768, entry['node_memory'])
        self.assertEqual(500, entry['node_disk'])

    def test_instance_count(self):
        servers = _servers_from_model(self.model)
        self.assertEqual(2, len(servers))

    def test_instance_mapping(self):
        entry = _find_server(
            self.model, '11111111-1111-1111-1111-111111111111'
        )
        self.assertIsNotNone(entry)
        self.assertEqual('compute-1', entry['node_hostname'])
        self.assertEqual(2, entry['server_vcpus'])
        self.assertEqual(4096, entry['server_memory'])
        self.assertEqual(20, entry['server_disk'])

        entry = _find_server(
            self.model, '22222222-2222-2222-2222-222222222222'
        )
        self.assertIsNotNone(entry)
        self.assertEqual('compute-2', entry['node_hostname'])
        self.assertEqual(4, entry['server_vcpus'])
        self.assertEqual(8192, entry['server_memory'])
        self.assertEqual(40, entry['server_disk'])

    def test_instance_project_id(self):
        entry = _find_server(
            self.model, '11111111-1111-1111-1111-111111111111'
        )
        self.assertEqual(
            'aaaaaaaa-1111-2222-3333-444444444444', entry['server_project_id']
        )


class TestNovaModelScoped(base.WatcherFunctionalTestCase):
    """Validate scope filtering on the data model via RPC.

    Scope is set on an AuditTemplate, then an audit inherits it.
    ``get_data_model(audit_uuid)`` returns the scoped model.
    """

    COMPUTE_TOPOLOGY = TOPOLOGY

    def setUp(self):
        super().setUp()
        self._template_counter = 0

    def _create_audit_with_scope(self, scope):
        """Create a ONESHOT audit with the given scope and wait for it.

        Uses the dummy strategy so the audit always succeeds
        regardless of topology — we only need the audit object
        in the DB with its scope for get_data_model().
        """
        self._template_counter += 1
        template_name = 'model-scope-%s-%d' % (
            self.id(),
            self._template_counter,
        )
        resp = self.admin_api.post(
            '/audit_templates',
            {
                'name': template_name,
                'goal': 'dummy',
                'strategy': 'dummy',
                'scope': scope,
            },
        )
        self.assertEqual(
            201, resp.status_code, 'Failed to create template: %s' % resp.text
        )
        template_uuid = resp.json()['uuid']

        resp = self.admin_api.post(
            '/audits',
            {'audit_type': 'ONESHOT', 'audit_template_uuid': template_uuid},
        )
        self.assertEqual(
            201, resp.status_code, 'Failed to create audit: %s' % resp.text
        )
        audit_uuid = resp.json()['uuid']
        self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')
        return audit_uuid

    # Scope: include by aggregate

    def test_scope_include_aggregate(self):
        """Only nodes in the 'prod' aggregate are in the scoped model."""
        scope = [{'compute': [{'host_aggregates': [{'name': 'prod'}]}]}]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        hostnames = {e['node_hostname'] for e in model}
        self.assertEqual({'compute-1', 'compute-2'}, hostnames)

        servers = _servers_from_model(model)
        server_uuids = {s['server_uuid'] for s in servers}
        # Only instances on compute-1 and compute-2
        self.assertNotIn(
            'dddd0001-0000-0000-0000-000000000001',
            server_uuids,
            'Instance on compute-3 (staging) should be excluded',
        )

    def test_scope_include_staging_aggregate(self):
        """Only compute-3 in the 'staging' aggregate is in the model."""
        scope = [{'compute': [{'host_aggregates': [{'name': 'staging'}]}]}]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)
        hostnames = {e['node_hostname'] for e in model}
        self.assertEqual({'compute-3'}, hostnames)

        servers = _servers_from_model(model)
        self.assertEqual(1, len(servers))
        self.assertEqual(
            'dddd0001-0000-0000-0000-000000000001', servers[0]['server_uuid']
        )

    # Scope: exclude compute node

    def test_scope_exclude_node(self):
        """Excluded node and its instances are removed from the model."""
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {'exclude': [{'compute_nodes': [{'name': 'compute-2'}]}]},
                ]
            }
        ]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        hostnames = {e['node_hostname'] for e in model}
        self.assertNotIn('compute-2', hostnames)
        self.assertIn('compute-1', hostnames)
        self.assertIn('compute-3', hostnames)

        server_uuids = {e['server_uuid'] for e in model if 'server_uuid' in e}
        self.assertNotIn('cccc0001-0000-0000-0000-000000000001', server_uuids)
        self.assertNotIn('cccc0002-0000-0000-0000-000000000002', server_uuids)

    def test_scope_exclude_multiple_nodes(self):
        """Multiple nodes can be excluded at once."""
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {
                        'exclude': [
                            {
                                'compute_nodes': [
                                    {'name': 'compute-2'},
                                    {'name': 'compute-3'},
                                ]
                            }
                        ]
                    },
                ]
            }
        ]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        hostnames = {e['node_hostname'] for e in model}
        # compute-2 and compute-3 are excluded; compute-empty is not
        # in any aggregate so the wildcard include already filters it.
        self.assertEqual({'compute-1'}, hostnames)

    # Scope: exclude instance

    def test_scope_exclude_instance(self):
        """Excluded instance has watcher_exclude=True but stays in model."""
        excluded_uuid = 'bbbb0002-0000-0000-0000-000000000002'
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {'exclude': [{'instances': [{'uuid': excluded_uuid}]}]},
                ]
            }
        ]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        entry = _find_server(model, excluded_uuid)
        self.assertIsNotNone(
            entry, 'Excluded instance should still be in the model'
        )
        self.assertTrue(
            entry['server_watcher_exclude'],
            'Excluded instance should have watcher_exclude=True',
        )

        # Non-excluded instance should have watcher_exclude=False
        other = _find_server(model, 'bbbb0001-0000-0000-0000-000000000001')
        self.assertFalse(other['server_watcher_exclude'])

    def test_scope_exclude_multiple_instances(self):
        """Multiple instances can be excluded."""
        excluded = [
            'bbbb0001-0000-0000-0000-000000000001',
            'bbbb0003-0000-0000-0000-000000000003',
        ]
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {
                        'exclude': [
                            {'instances': [{'uuid': u} for u in excluded]}
                        ]
                    },
                ]
            }
        ]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        for uuid in excluded:
            entry = _find_server(model, uuid)
            self.assertIsNotNone(entry)
            self.assertTrue(entry['server_watcher_exclude'])

        # Others not excluded
        non_excluded = _find_server(
            model, 'bbbb0005-0000-0000-0000-000000000005'
        )
        self.assertFalse(non_excluded['server_watcher_exclude'])

    # Scope: exclude by project

    def test_scope_exclude_project(self):
        """Instances belonging to excluded project have watcher_exclude."""
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {
                        'exclude': [
                            {
                                'projects': [
                                    {
                                        'uuid': 'bbbbbbbb-bbbb-'
                                        'bbbb-bbbb-bbbbbbbbbbbb'
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        # proj-bbb instances: ephemeral-vm (bbbb0003) and full-vm (bbbb0005)
        for uuid in [
            'bbbb0003-0000-0000-0000-000000000003',
            'bbbb0005-0000-0000-0000-000000000005',
        ]:
            entry = _find_server(model, uuid)
            self.assertTrue(
                entry['server_watcher_exclude'],
                'Instance %s (proj-bbb) should be excluded' % uuid,
            )

        # proj-aaa instance should not be excluded
        entry = _find_server(model, 'bbbb0001-0000-0000-0000-000000000001')
        self.assertFalse(entry['server_watcher_exclude'])

    # Scope: combined filters

    def test_scope_aggregate_plus_exclude_node(self):
        """Include aggregate + exclude node narrows the model."""
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': 'prod'}]},
                    {'exclude': [{'compute_nodes': [{'name': 'compute-2'}]}]},
                ]
            }
        ]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        hostnames = {e['node_hostname'] for e in model}
        # prod has compute-1 and compute-2; compute-2 is excluded
        self.assertEqual({'compute-1'}, hostnames)

    def test_scope_aggregate_plus_exclude_instance(self):
        """Include aggregate + exclude instance: node stays, flagged."""
        excluded_uuid = 'bbbb0004-0000-0000-0000-000000000004'
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': 'prod'}]},
                    {'exclude': [{'instances': [{'uuid': excluded_uuid}]}]},
                ]
            }
        ]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        hostnames = {e['node_hostname'] for e in model}
        self.assertEqual({'compute-1', 'compute-2'}, hostnames)

        entry = _find_server(model, excluded_uuid)
        self.assertTrue(entry['server_watcher_exclude'])

    # Scope: unscoped (no audit)

    def test_unscoped_returns_full_model(self):
        """get_data_model() without audit returns the complete model."""
        model = self.get_data_model()
        nodes = _nodes_from_model(model)
        servers = _servers_from_model(model)
        self.assertEqual(4, len(nodes))
        self.assertEqual(9, len(servers))

    # Disk accounting in scoped model

    def test_bfv_disk_in_scoped_model(self):
        """BFV disk accounting is preserved after scope filtering."""
        scope = [{'compute': [{'host_aggregates': [{'name': 'prod'}]}]}]
        audit_uuid = self._create_audit_with_scope(scope)
        model = self.get_data_model(audit_uuid=audit_uuid)

        # BFV instance with ephemeral+swap
        entry = _find_server(model, 'bbbb0006-0000-0000-0000-000000000006')
        expected = 0 + 10 + math.ceil(352 / 1024)  # 11
        self.assertEqual(expected, entry['server_disk'])

        # Regular instance
        entry = _find_server(model, 'bbbb0001-0000-0000-0000-000000000001')
        self.assertEqual(40, entry['server_disk'])
