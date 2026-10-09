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

"""Functional tests for the zone_migration strategy.

Tests that the strategy coordinates compute and storage migrations
for hardware maintenance.  Requires both the Nova/Placement emulator
(for compute topology) and the Cinder emulator (for storage topology).

The zone_migration strategy uses two data models (compute + storage)
and two helpers (NovaHelper + CinderHelper) to generate ``migrate``
(live/cold instance migration) and ``volume_migrate`` (volume
migrate/retype) actions.
"""

from watcher.tests.functional import base
from watcher.tests.functional import topology


# Compute topology
#
# 2 compute nodes with an aggregate containing both (required so
# the model builder sees them in scope).
#
# Instances on compute-src:
#   vm-active: ACTIVE (live-migratable)
#   vm-stopped: SHUTOFF (cold-migratable)
#   vm-attached: ACTIVE with an attached volume

COMPUTE_TOPOLOGY = topology.ComputeTopology(
    compute_nodes=[
        topology.ComputeNode(
            uuid='aaaa0001-0000-0000-0000-000000000001', hostname='compute-src'
        ),
        topology.ComputeNode(
            uuid='aaaa0002-0000-0000-0000-000000000002', hostname='compute-dst'
        ),
    ],
    instances=[
        topology.Instance(
            uuid='bbbb0001-0000-0000-0000-000000000001',
            name='vm-active',
            host='compute-src',
            state='active',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
        topology.Instance(
            uuid='bbbb0002-0000-0000-0000-000000000002',
            name='vm-stopped',
            host='compute-src',
            state='stopped',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
        topology.Instance(
            uuid='bbbb0003-0000-0000-0000-000000000003',
            name='vm-attached',
            host='compute-src',
            state='active',
            project_id=topology.DEFAULT_PROJECT_ID,
            volumes_attached=[{'id': 'cccc0001-0000-0000-0000-000000000001'}],
        ),
    ],
    aggregates=[
        topology.Aggregate(
            id=1, name='all-hosts', hosts=['compute-src', 'compute-dst']
        )
    ],
)

# Topology for scoped tests — 2 compute nodes, 2 aggregates, 2 instances.
# Simpler than the main topology to make scope effects clear.

SCOPED_COMPUTE_TOPOLOGY = topology.ComputeTopology(
    compute_nodes=[
        topology.ComputeNode(
            uuid='aaaa0001-0000-0000-0000-000000000001', hostname='compute-src'
        ),
        topology.ComputeNode(
            uuid='aaaa0002-0000-0000-0000-000000000002', hostname='compute-dst'
        ),
    ],
    instances=[
        topology.Instance(
            uuid='bbbb0001-0000-0000-0000-000000000001',
            name='vm-active',
            host='compute-src',
            state='active',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
        topology.Instance(
            uuid='bbbb0002-0000-0000-0000-000000000002',
            name='vm-stopped',
            host='compute-src',
            state='stopped',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
    ],
    aggregates=[
        topology.Aggregate(
            id=1, name='all-hosts', hosts=['compute-src', 'compute-dst']
        )
    ],
)

# Storage topology
#
# 2 storage nodes, 2 pools, 2 volume types (one per backend).
# Volumes on the source pool:
#   vol-attached: in-use, attached to vm-attached, on source pool
#   vol-free: available, not attached, on source pool
#   vol-dst: available, on destination pool (not a migration target)
#   vol-compatible-type: available, cross-compatible, on source pool

STORAGE_TOPOLOGY = topology.StorageTopology(
    storage_nodes=[
        topology.StorageNode(host='storage-src@backend1'),
        topology.StorageNode(host='storage-dst@backend2'),
    ],
    pools=[
        topology.Pool(
            name='storage-src@backend1#pool1',
            total_capacity_gb=1000,
            free_capacity_gb=800,
            provisioned_capacity_gb=200,
            allocated_capacity_gb=200,
            total_volumes=3,
            volume_backend_name='backend1',
        ),
        topology.Pool(
            name='storage-dst@backend2#pool1',
            total_capacity_gb=1000,
            free_capacity_gb=900,
            provisioned_capacity_gb=100,
            allocated_capacity_gb=100,
            total_volumes=1,
            volume_backend_name='backend2',
        ),
    ],
    volume_types=[
        topology.VolumeType(
            id='dddd0001-0000-0000-0000-000000000001',
            name='type1',
            extra_specs={'volume_backend_name': 'backend1'},
        ),
        topology.VolumeType(
            id='dddd0002-0000-0000-0000-000000000002',
            name='type2',
            extra_specs={'volume_backend_name': 'backend2'},
        ),
        topology.VolumeType(
            id='dddd0003-0000-0000-0000-000000000003', name='cross-compatible'
        ),
    ],
    volumes=[
        topology.Volume(
            id='cccc0001-0000-0000-0000-000000000001',
            name='vol-attached',
            size=50,
            status='in-use',
            volume_type='type1',
            host='storage-src@backend1#pool1',
            project_id=topology.DEFAULT_PROJECT_ID,
            attachments=[
                {
                    'server_id': 'bbbb0003-0000-0000-0000-000000000003',
                    'attachment_id': 'att-0001',
                }
            ],
        ),
        topology.Volume(
            id='cccc0002-0000-0000-0000-000000000002',
            name='vol-free',
            size=100,
            status='available',
            volume_type='type1',
            host='storage-src@backend1#pool1',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
        topology.Volume(
            id='cccc0003-0000-0000-0000-000000000003',
            name='vol-dst',
            size=50,
            status='available',
            volume_type='type2',
            host='storage-dst@backend2#pool1',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
        topology.Volume(
            id='cccc0004-0000-0000-0000-000000000004',
            name='vol-compatible-type',
            size=75,
            status='available',
            volume_type='cross-compatible',
            host='storage-src@backend1#pool1',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
    ],
)

# Ceph Storage topology
#
# Similar topology but simulates the capacity attributes
# included in Cinder API responses for Ceph backend

STORAGE_TOPOLOGY_CEPH = topology.StorageTopology(
    storage_nodes=[
        topology.StorageNode(host='host1@ceph1'),
        topology.StorageNode(host='host2@ceph2'),
    ],
    pools=[
        topology.Pool(
            name='host1@ceph1#ceph1',
            total_capacity_gb=1000,
            free_capacity_gb=800,
            allocated_capacity_gb=200,
            volume_backend_name='backend1',
        ),
        topology.Pool(
            name='host2@ceph2#ceph2',
            total_capacity_gb=1000,
            free_capacity_gb=900,
            provisioned_capacity_gb=100,
            allocated_capacity_gb=100,
            total_volumes=1,
            volume_backend_name='backend2',
        ),
    ],
    volume_types=[
        topology.VolumeType(
            id='dddd0001-0000-0000-0000-000000000001',
            name='ceph1',
            extra_specs={'volume_backend_name': 'backend1'},
        ),
        topology.VolumeType(
            id='dddd0002-0000-0000-0000-000000000002',
            name='ceph2',
            extra_specs={'volume_backend_name': 'backend2'},
        ),
        topology.VolumeType(
            id='dddd0003-0000-0000-0000-000000000003', name='cross-compatible'
        ),
    ],
    volumes=[
        topology.Volume(
            id='cccc0001-0000-0000-0000-000000000001',
            name='vol-attached',
            size=50,
            status='in-use',
            volume_type='ceph1',
            host='host1@ceph1#ceph1',
            project_id=topology.DEFAULT_PROJECT_ID,
            attachments=[
                {
                    'server_id': 'bbbb0003-0000-0000-0000-000000000003',
                    'attachment_id': 'att-0001',
                }
            ],
        ),
        topology.Volume(
            id='cccc0002-0000-0000-0000-000000000002',
            name='vol-free',
            size=100,
            status='available',
            volume_type='ceph1',
            host='host1@ceph1#ceph1',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
        topology.Volume(
            id='cccc0003-0000-0000-0000-000000000003',
            name='vol-dst',
            size=50,
            status='available',
            volume_type='ceph2',
            host='host2@ceph2#ceph2',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
        topology.Volume(
            id='cccc0004-0000-0000-0000-000000000004',
            name='vol-compatible-type',
            size=75,
            status='available',
            volume_type='cross-compatible',
            host='host1@ceph1#ceph1',
            project_id=topology.DEFAULT_PROJECT_ID,
        ),
    ],
)


class TestZoneMigration(base.WatcherFunctionalTestCase):
    """Tests for the zone_migration strategy with Cinder + Nova."""

    COMPUTE_TOPOLOGY = COMPUTE_TOPOLOGY
    STORAGE_TOPOLOGY = STORAGE_TOPOLOGY

    def setUp(self):
        super().setUp()
        self._template_counter = 0

    def _run_scoped_audit(self, scope, parameters):
        """Create a zone_migration audit with scope and return results.

        Scope must be set on an AuditTemplate because the Audit API
        has ``scope`` as readonly.  The audit inherits scope from
        the template.

        Returns (actions, action_plan).
        """
        self._template_counter += 1
        template_name = 'scoped-zm-%s-%d' % (self.id(), self._template_counter)

        resp = self.admin_api.post(
            '/audit_templates',
            {
                'name': template_name,
                'goal': 'hardware_maintenance',
                'strategy': 'zone_migration',
                'scope': scope,
            },
        )
        self.assertEqual(
            201,
            resp.status_code,
            'Failed to create audit template: %s' % resp.text,
        )
        template_uuid = resp.json()['uuid']

        resp = self.admin_api.post(
            '/audits',
            {
                'audit_type': 'ONESHOT',
                'audit_template_uuid': template_uuid,
                'parameters': parameters,
            },
        )
        self.assertEqual(
            201, resp.status_code, 'Failed to create audit: %s' % resp.text
        )
        audit_uuid = resp.json()['uuid']

        self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')

        resp = self.admin_api.get('/action_plans?audit_uuid=%s' % audit_uuid)
        action_plans = resp.json()['action_plans']
        self.assertEqual(1, len(action_plans))

        ap_uuid = action_plans[0]['uuid']
        ap = self.admin_api.get('/action_plans/%s' % ap_uuid).json()

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        raw_actions = resp.json()['actions']

        details = []
        for action in raw_actions:
            detail = self.admin_api.get('/actions/%s' % action['uuid']).json()
            details.append(detail)

        return details, ap

    def _run_audit(self, parameters):
        """Create a zone_migration audit and return (actions, action_plan)."""
        resp = self.admin_api.post(
            '/audits',
            {
                'audit_type': 'ONESHOT',
                'goal': 'hardware_maintenance',
                'strategy': 'zone_migration',
                'parameters': parameters,
            },
        )
        self.assertEqual(
            201, resp.status_code, 'Failed to create audit: %s' % resp.text
        )
        audit_uuid = resp.json()['uuid']

        self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')

        resp = self.admin_api.get('/action_plans?audit_uuid=%s' % audit_uuid)
        action_plans = resp.json()['action_plans']
        self.assertEqual(1, len(action_plans))

        ap_uuid = action_plans[0]['uuid']
        ap = self.admin_api.get('/action_plans/%s' % ap_uuid).json()

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        raw_actions = resp.json()['actions']

        details = []
        for action in raw_actions:
            detail = self.admin_api.get('/actions/%s' % action['uuid']).json()
            details.append(detail)

        return details, ap

    def _assert_efficacy_indicators(
        self,
        ap,
        planned_live=0,
        planned_cold=0,
        planned_volume=0,
        live=None,
        cold=None,
        volume=None,
    ):
        """Assert efficacy indicators on the action plan.

        :param planned_live: Expected planned_live_migrate_instance_count.
        :param planned_cold: Expected planned_cold_migrate_instance_count.
        :param planned_volume: Expected planned_volume_migrate_count.
        :param live: Expected live_migrate_instance_count (defaults to
            planned_live — they differ only when parallel limits truncate).
        :param cold: Expected cold_migrate_instance_count (same default).
        :param volume: Expected volume_migrate_count (same default).
        """
        if live is None:
            live = planned_live
        if cold is None:
            cold = planned_cold
        if volume is None:
            volume = planned_volume

        indicators = {
            ei['name']: ei['value'] for ei in ap.get('efficacy_indicators', [])
        }
        self.assertEqual(
            float(live), indicators['live_migrate_instance_count']
        )
        self.assertEqual(
            float(planned_live),
            indicators['planned_live_migrate_instance_count'],
        )
        self.assertEqual(
            float(cold), indicators['cold_migrate_instance_count']
        )
        self.assertEqual(
            float(planned_cold),
            indicators['planned_cold_migrate_instance_count'],
        )
        self.assertEqual(float(volume), indicators['volume_migrate_count'])
        self.assertEqual(
            float(planned_volume), indicators['planned_volume_migrate_count']
        )

    def test_volume_migrate(self):
        """Volume migration when src/dst pools share the same type.

        Configures storage_pools with src_pool→dst_pool (no src_type).
        All volumes on the source pool are migrated regardless of type.
        Expects volume_migrate actions with migration_type=migrate.
        """
        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 4,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(3, len(vol_actions))

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-attached',
            migration_type='migrate',
            destination_node='storage-dst@backend2#pool1',
        )

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-free',
            migration_type='migrate',
            destination_node='storage-dst@backend2#pool1',
        )

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-compatible-type',
            migration_type='migrate',
            destination_node='storage-dst@backend2#pool1',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_volume=3)

    def test_volume_migrate_ceph(self):
        """Volume migration when src/dst pools share the same type with ceph.

        Configures storage_pools with src_pool→dst_pool (no src_type).
        All volumes on the source pool are migrated regardless of type.
        Expects volume_migrate actions with migration_type=migrate.
        """

        self.load_storage_topology(STORAGE_TOPOLOGY_CEPH)

        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'host1@ceph1#ceph1',
                        'dst_pool': 'host2@ceph2#ceph2',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 4,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(3, len(vol_actions))

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-attached',
            migration_type='migrate',
            destination_node='host2@ceph2#ceph2',
        )

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-free',
            migration_type='migrate',
            destination_node='host2@ceph2#ceph2',
        )

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-compatible-type',
            migration_type='migrate',
            destination_node='host2@ceph2#ceph2',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_volume=3)

    def test_volume_retype(self):
        """Volume retype when src_type differs from dst_type.

        Configures storage_pools with src_pool + dst_type (no dst_pool).
        Expects volume_migrate actions with migration_type=retype.
        """
        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'src_type': 'type1',
                        'dst_type': 'type2',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(2, len(vol_actions))

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-attached',
            migration_type='retype',
            destination_type='type2',
        )

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-free',
            migration_type='retype',
            destination_type='type2',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_volume=2)

        # Execute the action plan — retype does not validate backend
        # compatibility, so execution should succeed.
        ap = self._execute_action_plan(ap['uuid'])
        self.assertEqual('SUCCEEDED', ap['state'])

    def test_volume_retype_ceph(self):
        """Volume retype when src_type differs from dst_type in ceph bckends

        Configures storage_pools with src_pool + dst_type (no dst_pool).
        Expects volume_migrate actions with migration_type=retype.
        """

        self.load_storage_topology(STORAGE_TOPOLOGY_CEPH)

        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'host1@ceph1#ceph1',
                        'src_type': 'ceph1',
                        'dst_type': 'ceph2',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(2, len(vol_actions))

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-attached',
            migration_type='retype',
            destination_type='ceph2',
        )

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-free',
            migration_type='retype',
            destination_type='ceph2',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_volume=2)

        # Execute the action plan — retype does not validate backend
        # compatibility, so execution should succeed.
        ap = self._execute_action_plan(ap['uuid'])
        self.assertEqual('SUCCEEDED', ap['state'])

    def test_volume_migrate_with_src_type_filter(self):
        """src_type filters which volumes are migrated from a pool.

        When src_type is specified alongside dst_pool, only volumes
        whose volume_type matches src_type are migrated. vol-free
        and vol-attached are type1, vol-compatible-type is
        cross-compatible — all on the same source pool. With
        src_type=type1, only the type1 volumes should be migrated.
        """
        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'src_type': 'type1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 4,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]

        self.assertEqual(2, len(vol_actions))

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-attached',
            migration_type='migrate',
            destination_node='storage-dst@backend2#pool1',
        )

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-free',
            migration_type='migrate',
            destination_node='storage-dst@backend2#pool1',
        )
        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_volume=2)

    def test_instance_live_migration(self):
        """Active instance is live-migrated to the destination node."""
        # Use only the active instance (not stopped, not attached)
        self.load_topology(
            topology.ComputeTopology(
                compute_nodes=COMPUTE_TOPOLOGY.compute_nodes,
                instances=[COMPUTE_TOPOLOGY.instances[0]],
                aggregates=COMPUTE_TOPOLOGY.aggregates,
            )
        )

        actions, ap = self._run_audit(
            {
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(1, len(migrate_actions))

        self._assert_action(
            migrate_actions,
            'migrate',
            resource_name='vm-active',
            migration_type='live',
            destination_node='compute-dst',
            source_node='compute-src',
        )
        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_live=1)

        # Execute the action plan — Nova emulator handles
        # os-migrateLive by moving the server to the destination host.
        ap = self._execute_action_plan(ap['uuid'])
        self.assertEqual('SUCCEEDED', ap['state'])

    def test_instance_cold_migration(self):
        """Stopped instance is cold-migrated to the destination node."""
        # Use only the stopped instance
        self.load_topology(
            topology.ComputeTopology(
                compute_nodes=COMPUTE_TOPOLOGY.compute_nodes,
                instances=[COMPUTE_TOPOLOGY.instances[1]],
                aggregates=COMPUTE_TOPOLOGY.aggregates,
            )
        )

        actions, ap = self._run_audit(
            {
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(1, len(migrate_actions))

        self._assert_action(
            migrate_actions,
            'migrate',
            resource_name='vm-stopped',
            migration_type='cold',
            destination_node='compute-dst',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_cold=1)

        # Execute — Nova emulator handles migrate + confirmResize,
        # restoring SHUTOFF status after confirmation.
        ap = self._execute_action_plan(ap['uuid'])
        self.assertEqual('SUCCEEDED', ap['state'])

    def test_combined_compute_and_storage(self):
        """Both compute and storage migrations in a single audit.

        Configures both compute_nodes and storage_pools.  Expects
        migrate actions for instances AND volume_migrate actions
        for volumes.
        """
        actions, ap = self._run_audit(
            {
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 10,
                'parallel_per_pool': 4,
                'parallel_per_node': 4,
            }
        )

        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-active',
            migration_type='live',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-attached',
            migration_type='live',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-stopped',
            migration_type='cold',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'volume_migrate',
            migration_type='migrate',
            resource_name='vol-attached',
            destination_node='storage-dst@backend2#pool1',
        )
        self._assert_action(
            actions,
            'volume_migrate',
            migration_type='migrate',
            resource_name='vol-free',
            destination_node='storage-dst@backend2#pool1',
        )
        self._assert_action(
            actions,
            'volume_migrate',
            migration_type='migrate',
            resource_name='vol-compatible-type',
            destination_node='storage-dst@backend2#pool1',
        )

        # 2 active instances (vm-active + vm-attached) → 2 live,
        # 1 stopped (vm-stopped) → 1 cold, 3 volumes on src pool
        self._assert_efficacy_indicators(
            ap, planned_live=2, planned_cold=1, planned_volume=3
        )

    def test_with_attached_volume(self):
        """Attached volume triggers instance migration alongside.

        When with_attached_volume=True and the volume is attached to
        an instance that is also in the compute migration target list,
        the strategy should migrate both the volume and the instance.
        """
        actions, ap = self._run_audit(
            {
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'with_attached_volume': True,
                'parallel_total': 10,
                'parallel_per_pool': 4,
                'parallel_per_node': 4,
            }
        )

        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-active',
            migration_type='live',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-attached',
            migration_type='live',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-stopped',
            migration_type='cold',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'volume_migrate',
            migration_type='migrate',
            resource_name='vol-attached',
            destination_node='storage-dst@backend2#pool1',
        )
        self._assert_action(
            actions,
            'volume_migrate',
            migration_type='migrate',
            resource_name='vol-free',
            destination_node='storage-dst@backend2#pool1',
        )
        self._assert_action(
            actions,
            'volume_migrate',
            migration_type='migrate',
            resource_name='vol-compatible-type',
            destination_node='storage-dst@backend2#pool1',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(
            ap, planned_live=2, planned_cold=1, planned_volume=3
        )

    def test_parallel_total_limit(self):
        """parallel_total limits the total number of actions generated.

        With parallel_total=1, only one action should be generated
        even though multiple volumes/instances are eligible.
        """
        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 1,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(1, len(vol_actions))
        self.assertEqual('RECOMMENDED', ap['state'])
        # 3 volumes eligible but only 1 planned due to parallel_total=1
        self._assert_efficacy_indicators(ap, planned_volume=1, volume=3)

    def test_storage_model_built(self):
        """Verify the storage data model is built from Cinder emulator data.

        The Cinder collector should build a StorageModelRoot containing
        the expected storage nodes, pools, and volumes.
        """
        # Trigger model build by running a minimal audit
        self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        model = self.get_storage_data_model()
        self.assertIsNotNone(model)

        all_nodes = model.get_all_storage_nodes()
        node_hosts = {n.host for n in all_nodes.values()}
        self.assertIn('storage-src@backend1', node_hosts)
        self.assertIn('storage-dst@backend2', node_hosts)

        pool_names = set()
        for node in all_nodes.values():
            for pool in model.get_node_pools(node):
                pool_names.add(pool.name)
        self.assertIn('storage-src@backend1#pool1', pool_names)
        self.assertIn('storage-dst@backend2#pool1', pool_names)

        all_volumes = model.get_all_volumes()
        vol_uuids = set(all_volumes.keys())
        self.assertIn('cccc0001-0000-0000-0000-000000000001', vol_uuids)
        self.assertIn('cccc0002-0000-0000-0000-000000000002', vol_uuids)
        self.assertIn('cccc0003-0000-0000-0000-000000000003', vol_uuids)
        self.assertIn('cccc0004-0000-0000-0000-000000000004', vol_uuids)

    def test_storage_model_built_ceph(self):
        """Verify the storage data model is built from Cinder emulator data.

        The Cinder collector should build a StorageModelRoot containing
        the expected storage nodes, pools, and volumes with ceph simulated
        pools
        """
        # Trigger model build by running a minimal audit
        self.load_storage_topology(STORAGE_TOPOLOGY_CEPH)
        self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'host1@ceph1#ceph1',
                        'dst_pool': 'host2@ceph2#ceph2',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        model = self.get_storage_data_model()
        self.assertIsNotNone(model)

        all_nodes = model.get_all_storage_nodes()
        node_hosts = {n.host for n in all_nodes.values()}
        self.assertIn('host1@ceph1', node_hosts)
        self.assertIn('host2@ceph2', node_hosts)

        pool_names = set()
        for node in all_nodes.values():
            for pool in model.get_node_pools(node):
                pool_names.add(pool.name)
        self.assertIn('host1@ceph1#ceph1', pool_names)
        self.assertIn('host2@ceph2#ceph2', pool_names)

        all_volumes = model.get_all_volumes()
        vol_uuids = set(all_volumes.keys())
        self.assertIn('cccc0001-0000-0000-0000-000000000001', vol_uuids)
        self.assertIn('cccc0002-0000-0000-0000-000000000002', vol_uuids)
        self.assertIn('cccc0003-0000-0000-0000-000000000003', vol_uuids)
        self.assertIn('cccc0004-0000-0000-0000-000000000004', vol_uuids)

    def test_no_targets_succeeds_with_empty_plan(self):
        """Audit with no matching targets still succeeds.

        When storage_pools references a pool that doesn't exist in the
        topology, no volumes match and the audit completes with an
        empty action plan (SUCCEEDED state, no RECOMMENDED).
        """
        resp = self.admin_api.post(
            '/audits',
            {
                'audit_type': 'ONESHOT',
                'goal': 'hardware_maintenance',
                'strategy': 'zone_migration',
                'parameters': {
                    'storage_pools': [
                        {
                            'src_pool': 'nonexistent@backend#pool',
                            'dst_pool': 'storage-dst@backend2#pool1',
                        }
                    ],
                    'parallel_total': 6,
                    'parallel_per_pool': 2,
                    'parallel_per_node': 2,
                },
            },
        )
        self.assertEqual(201, resp.status_code)
        audit_uuid = resp.json()['uuid']

        self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')

        resp = self.admin_api.get('/action_plans?audit_uuid=%s' % audit_uuid)
        ap_uuid = resp.json()['action_plans'][0]['uuid']
        ap = self.admin_api.get('/action_plans/%s' % ap_uuid).json()
        self.assertEqual('SUCCEEDED', ap['state'])

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        self.assertEqual(0, len(resp.json()['actions']))

    def test_execute_volume_migrate_incompatible_type(self):
        """Volume migrate fails when type extra_specs don't match dst pool.

        type1 has extra_specs volume_backend_name=backend1 but the
        destination pool's capabilities have volume_backend_name=backend2.
        cinder_helper.migrate() calls get_volume_types_for_pool() which
        uses _check_backend_matches_type() to verify compatibility.
        The mismatch causes the action to fail.
        """
        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'src_type': 'type1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 4,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(2, len(vol_actions))
        self.assertEqual('RECOMMENDED', ap['state'])

        ap = self._execute_action_plan(ap['uuid'], expected_state='FAILED')
        self.assertEqual('FAILED', ap['state'])

    def test_execute_volume_migrate_compatible_type(self):
        """Volume pool-migrate succeeds when type matches dst pool.

        cross-compatible type has no extra_specs volume_backend_name
        so it's compatible with any destination pool. Only vol-compatible-type
        is selected via src_type filter, migrated to backend2 pool, and
        execution should succeed.
        """
        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'src_type': 'cross-compatible',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 6,
                'parallel_per_pool': 4,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(1, len(vol_actions))

        self._assert_action(
            vol_actions,
            'volume_migrate',
            resource_name='vol-compatible-type',
            migration_type='migrate',
            destination_node='storage-dst@backend2#pool1',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_volume=1)

        ap = self._execute_action_plan(ap['uuid'])
        self.assertEqual('SUCCEEDED', ap['state'])

    def test_parallel_per_pool_limit(self):
        """parallel_per_pool limits actions per storage pool.

        Builds a storage topology entirely via the builder pattern:
        two pools sharing one volume type, with 10 volumes on the
        source pool.  With parallel_per_pool=8, only 8 volume_migrate
        actions should be generated even though all 10 volumes on the
        source pool are eligible.
        """
        storage_topology = (
            topology.StorageTopology()
            .add_storage_node('storage-src@backend1')
            .add_storage_node('storage-dst@backend2')
            .add_pool(
                'storage-src@backend1#pool1',
                total_capacity_gb=1000,
                free_capacity_gb=500,
                volume_backend_name='backend1',
            )
            .add_pool(
                'storage-dst@backend2#pool1',
                total_capacity_gb=1000,
                free_capacity_gb=1000,
                volume_backend_name='backend1',
            )
            .add_volume_type(
                'type1', extra_specs={'volume_backend_name': 'backend1'}
            )
            .add_volumes(
                pools=['storage-src@backend1#pool1'],
                count=10,
                volume_type='type1',
                project_id=topology.DEFAULT_PROJECT_ID,
            )
        )
        self.load_storage_topology(storage_topology)

        actions, ap = self._run_audit(
            {
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'parallel_total': 10,
                'parallel_per_pool': 8,
                'parallel_per_node': 2,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        self.assertEqual(8, len(vol_actions))
        self.assertEqual('RECOMMENDED', ap['state'])
        # 10 eligible but only 8 planned due to per_pool limit
        self._assert_efficacy_indicators(ap, planned_volume=8, volume=10)

    def test_parallel_per_node_limit(self):
        """parallel_per_node limits actions per compute node.

        With parallel_per_node=1 and 3 instances on compute-src
        (vm-active, vm-stopped, vm-attached), only 1 migrate action
        should be generated even though parallel_total allows more.
        """
        actions, ap = self._run_audit(
            {
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 1,
            }
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(1, len(migrate_actions))
        self.assertEqual('RECOMMENDED', ap['state'])

    def test_dst_node_omitted(self):
        """Omitting dst_node lets Nova auto-select the destination.

        When compute_nodes has src_node but no dst_node, the strategy
        generates a migrate action without destination_node in the
        parameters.  Nova picks the destination.
        """
        # Use only the active instance
        self.load_topology(
            topology.ComputeTopology(
                compute_nodes=COMPUTE_TOPOLOGY.compute_nodes,
                instances=[COMPUTE_TOPOLOGY.instances[0]],
                aggregates=COMPUTE_TOPOLOGY.aggregates,
            )
        )

        actions, ap = self._run_audit(
            {
                'compute_nodes': [{'src_node': 'compute-src'}],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            }
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(1, len(migrate_actions))

        params = migrate_actions[0]['input_parameters']
        self.assertNotIn('destination_node', params)
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-active',
            migration_type='live',
            source_node='compute-src',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_live=1)

        # Execute — Nova emulator auto-selects destination when
        # no host is specified in os-migrateLive.
        ap = self._execute_action_plan(ap['uuid'])
        self.assertEqual('SUCCEEDED', ap['state'])

    def test_with_attached_volume_instance_not_in_targets(self):
        """Attached instance is NOT migrated when its node is not a target.

        A third compute node is appended to a copy of the shared
        topology via the builder pattern (``add_computes()`` /
        ``add_instances()``), yielding ``compute-other-1`` hosting
        ``vm-other-1`` as the compute migration source.  vm-attached
        lives on compute-src which is NOT in compute_nodes.  Even
        though vol-attached is migrated and with_attached_volume=True,
        vm-attached should NOT be migrated because its server_id is
        not in instance_target_ids.  vm-other-1 IS migrated because
        it is on the compute source node.
        """
        compute_topology = topology.ComputeTopology(
            compute_nodes=list(COMPUTE_TOPOLOGY.compute_nodes),
            instances=list(COMPUTE_TOPOLOGY.instances),
            aggregates=[
                topology.Aggregate(
                    id=1,
                    name='all-hosts',
                    hosts=['compute-src', 'compute-dst', 'compute-other-1'],
                )
            ],
        )
        compute_topology.add_computes(count=1, hostname_prefix='compute-other')
        compute_topology.add_instances(
            computes=['compute-other-1'],
            count=1,
            name_prefix='vm-other',
            vcpus=2,
            memory=2048,
            disk=10,
            state='active',
        )
        self.load_topology(compute_topology)

        actions, ap = self._run_audit(
            {
                'compute_nodes': [
                    {'src_node': 'compute-other-1', 'dst_node': 'compute-dst'}
                ],
                'storage_pools': [
                    {
                        'src_pool': 'storage-src@backend1#pool1',
                        'dst_pool': 'storage-dst@backend2#pool1',
                    }
                ],
                'with_attached_volume': True,
                'parallel_total': 10,
                'parallel_per_pool': 4,
                'parallel_per_node': 4,
            }
        )

        vol_actions = [
            a for a in actions if a['action_type'] == 'volume_migrate'
        ]
        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']

        self._assert_action(
            actions,
            'volume_migrate',
            resource_name='vol-attached',
            migration_type='migrate',
            destination_node='storage-dst@backend2#pool1',
        )
        self.assertEqual(3, len(vol_actions))

        # vm-other-1 on compute-other-1 IS in compute targets → migrated
        self.assertEqual(1, len(migrate_actions))
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-other-1',
            migration_type='live',
            destination_node='compute-dst',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_live=1, planned_volume=3)

    # Scope: host_aggregates include

    def test_scope_aggregate_include(self):
        """Scope including 'all-hosts' aggregate sees both nodes.

        With both compute-src and compute-dst in scope, the strategy
        behaves the same as without scope: vm-active is live-migrated
        and vm-stopped is cold-migrated to compute-dst.
        """
        self.load_topology(SCOPED_COMPUTE_TOPOLOGY)

        scope = [{'compute': [{'host_aggregates': [{'name': 'all-hosts'}]}]}]

        actions, ap = self._run_scoped_audit(
            scope=scope,
            parameters={
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            },
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(2, len(migrate_actions))

        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-active',
            migration_type='live',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-stopped',
            migration_type='cold',
            destination_node='compute-dst',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_live=1, planned_cold=1)

    # Scope: exclude source compute node

    def test_scope_exclude_src_node(self):
        """Excluding compute-src removes it and its instances from model.

        When compute-src is excluded, its instances are removed from
        the scoped model. get_instances() finds no instances matching
        the src_node, so the audit produces an empty action plan.
        """
        self.load_topology(SCOPED_COMPUTE_TOPOLOGY)

        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {
                        'exclude': [
                            {'compute_nodes': [{'name': 'compute-src'}]}
                        ]
                    },
                ]
            }
        ]

        actions, ap = self._run_scoped_audit(
            scope=scope,
            parameters={
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            },
        )

        self.assertEqual(0, len(actions))
        self.assertEqual('SUCCEEDED', ap['state'])

    # Scope: exclude destination compute node

    def test_scope_exclude_dst_node(self):
        """Excluding compute-dst does not prevent migrations.

        zone_migration passes dst_node as a name from the strategy
        parameters without verifying it exists in the scoped model.
        Instances on compute-src are still visible and migrate with
        destination_node='compute-dst'.
        """
        self.load_topology(SCOPED_COMPUTE_TOPOLOGY)

        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {
                        'exclude': [
                            {'compute_nodes': [{'name': 'compute-dst'}]}
                        ]
                    },
                ]
            }
        ]

        actions, ap = self._run_scoped_audit(
            scope=scope,
            parameters={
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            },
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(2, len(migrate_actions))

        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-active',
            migration_type='live',
            destination_node='compute-dst',
        )
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-stopped',
            migration_type='cold',
            destination_node='compute-dst',
        )

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_live=1, planned_cold=1)

    # Scope: exclude specific instance

    def test_scope_exclude_instance(self):
        """Excluded instance is not migrated.

        The scope marks vm-active with watcher_exclude=True, and
        zone_migration checks this flag before adding an instance to
        the migration plan, so only vm-stopped (not excluded) is
        migrated.
        """
        self.load_topology(SCOPED_COMPUTE_TOPOLOGY)

        excluded_uuid = 'bbbb0001-0000-0000-0000-000000000001'

        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {'exclude': [{'instances': [{'uuid': excluded_uuid}]}]},
                ]
            }
        ]

        actions, ap = self._run_scoped_audit(
            scope=scope,
            parameters={
                'compute_nodes': [
                    {'src_node': 'compute-src', 'dst_node': 'compute-dst'}
                ],
                'parallel_total': 6,
                'parallel_per_pool': 2,
                'parallel_per_node': 2,
            },
        )

        # vm-stopped should always be migrated
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-stopped',
            migration_type='cold',
            destination_node='compute-dst',
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']

        # vm-active is excluded from scope via watcher_exclude, so it
        # is not migrated; only vm-stopped is.
        self.assertEqual(1, len(migrate_actions))
        migrate_names = {
            a['input_parameters']['resource_name'] for a in migrate_actions
        }
        self.assertNotIn('vm-active', migrate_names)

        self.assertEqual('RECOMMENDED', ap['state'])
        self._assert_efficacy_indicators(ap, planned_cold=1)
