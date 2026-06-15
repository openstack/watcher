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

"""Functional tests for the host_maintenance strategy.

Tests the complete audit -> strategy -> action plan -> applier flow
using emulated Nova and Placement APIs with realistic cluster
topologies, instead of the dummy strategy with a fake empty model.

Each test method defines its own topology via load_topology(),
so different scenarios (3-node cluster, insufficient backup, etc.)
can coexist in the same test class.
"""

from watcher.tests.functional import base
from watcher.tests.functional import topology


THREE_NODE_TOPOLOGY = (
    topology.ComputeTopology()
    .add_computes(count=3)
    .add_instances(computes=['compute-1'], count=2, vcpus=2)
    .add_instances(computes=['compute-2'], count=1, vcpus=2)
)


MIXED_STATE_TOPOLOGY = (
    topology.ComputeTopology()
    .add_computes(count=2, vcpus=64, memory=131072, disk=2000)
    .add_instances(computes=['compute-1'], count=5, vcpus=2)
    .add_instances(computes=['compute-1'], count=3, vcpus=2, state='stopped')
)

TIGHT_TOPOLOGY = (
    topology.ComputeTopology()
    .add_computes(count=2, vcpus=4, memory=8192, disk=100)
    .add_instances(computes=['compute-1'], count=2, vcpus=2, memory=2048)
    .add_instances(computes=['compute-2'], count=1, vcpus=2, memory=2048)
)


class TestHostMaintenance(base.WatcherFunctionalTestCase):
    """Full end-to-end tests of the host_maintenance strategy."""

    COMPUTE_TOPOLOGY = topology.ComputeTopology()

    def setUp(self):
        super().setUp()
        self.flags(migration_max_retries=5, group='nova')
        self.flags(migration_interval=0.1, group='nova')

    def _create_audit_and_get_actions(self, parameters):
        """Create a host_maintenance audit and return action details.

        Creates an audit, waits for SUCCEEDED, and returns the full
        action detail list.  Call ``self.load_topology()`` before this
        method if the test needs a specific topology.
        """
        resp = self.admin_api.post(
            '/audits',
            {
                'audit_type': 'ONESHOT',
                'goal': 'cluster_maintaining',
                'strategy': 'host_maintenance',
                'parameters': parameters,
            },
        )
        self.assertEqual(201, resp.status_code)
        audit_uuid = resp.json()['uuid']

        self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')

        resp = self.admin_api.get('/action_plans?audit_uuid=%s' % audit_uuid)
        action_plans = resp.json()['action_plans']
        self.assertEqual(1, len(action_plans))
        ap_uuid = action_plans[0]['uuid']

        resp = self.admin_api.get('/action_plans/%s' % ap_uuid)
        self.assertEqual('RECOMMENDED', resp.json()['state'])

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        actions = resp.json()['actions']

        details = []
        for action in actions:
            detail = self.admin_api.get('/actions/%s' % action['uuid']).json()
            details.append(detail)
        return details, ap_uuid

    def test_host_maintenance_with_backup_node(self):
        """Test migrating all VMs from compute-1 to compute-2."""
        self.load_topology(THREE_NODE_TOPOLOGY)
        actions, ap_uuid = self._create_audit_and_get_actions(
            {'maintenance_node': 'compute-1', 'backup_node': 'compute-2'}
        )

        # 1 disable + 2 live migrations = 3 actions
        self.assertEqual(3, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=THREE_NODE_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-1',
            resource_id=THREE_NODE_TOPOLOGY.instances[0].uuid,
            migration_type='live',
            destination_node='compute-2',
        )

        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-2',
            resource_id=THREE_NODE_TOPOLOGY.instances[1].uuid,
            migration_type='live',
            destination_node='compute-2',
        )

        # Execute the action plan and verify all actions succeed
        resp = self.admin_api.patch(
            '/action_plans/%s' % ap_uuid,
            [{'op': 'replace', 'path': '/state', 'value': 'PENDING'}],
        )
        self.assertEqual(200, resp.status_code)

        ap = self._wait_for_action_plan_state(ap_uuid, 'SUCCEEDED')
        self.assertEqual('SUCCEEDED', ap['state'])

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        for action in resp.json()['actions']:
            self.assertEqual(
                'SUCCEEDED',
                action['state'],
                'Action %s (%s) is %s, not SUCCEEDED'
                % (action['uuid'], action['action_type'], action['state']),
            )

        emulator = self.env.nova_fixture.nova_emulator
        for inst in THREE_NODE_TOPOLOGY.instances[:2]:
            server = emulator.servers[inst.uuid]
            self.assertEqual(
                'compute-2',
                server['OS-EXT-SRV-ATTR:host'],
                'Instance %s should have moved to compute-2' % inst.uuid,
            )

    def test_host_maintenance_without_backup_node(self):
        """Test migrating all VMs from compute-1 via nova-scheduler."""
        self.load_topology(THREE_NODE_TOPOLOGY)
        actions, ap_uuid = self._create_audit_and_get_actions(
            {'maintenance_node': 'compute-1'}
        )

        # 1 disable + 2 live migrations = 3 actions
        self.assertEqual(3, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=THREE_NODE_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        for inst in THREE_NODE_TOPOLOGY.instances[:2]:
            action = self._assert_action(
                actions,
                'migrate',
                resource_name=inst.name,
                resource_id=inst.uuid,
                migration_type='live',
            )
            self.assertNotIn(
                'destination_node',
                action['input_parameters'],
                'Migration for %s should not have a destination '
                '(nova-scheduler decides)' % inst.name,
            )

        # Execute and verify
        resp = self.admin_api.patch(
            '/action_plans/%s' % ap_uuid,
            [{'op': 'replace', 'path': '/state', 'value': 'PENDING'}],
        )
        self.assertEqual(200, resp.status_code)

        ap = self._wait_for_action_plan_state(ap_uuid, 'SUCCEEDED')
        self.assertEqual('SUCCEEDED', ap['state'])

    def test_host_maintenance_empty_node(self):
        """Test maintaining a node with no VMs (compute-3)."""
        self.load_topology(THREE_NODE_TOPOLOGY)
        actions, _ = self._create_audit_and_get_actions(
            {'maintenance_node': 'compute-3'}
        )

        # Only 1 disable action, no migrations
        self.assertEqual(1, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-3',
            resource_id=THREE_NODE_TOPOLOGY.compute_nodes[2].uuid,
            state='disabled',
        )

    def test_backup_insufficient_capacity(self):
        """Migrations should have no destination when backup is too small.

        Topology (2 nodes, tight resources):

            compute-1: 4 vcpus / 8192 MB, 2 VMs using 2+2=4 vcpus
            compute-2: 4 vcpus / 8192 MB, 1 VM  using 2 vcpus
                       -> only 2 vcpus free, cannot absorb 4

        host_maintenance falls back to try_maintain which plans
        migrations without a destination_node (nova-scheduler decides).
        """
        self.load_topology(TIGHT_TOPOLOGY)
        actions, _ = self._create_audit_and_get_actions(
            {'maintenance_node': 'compute-1', 'backup_node': 'compute-2'}
        )

        # 1 disable + 2 live migrations = 3 actions
        self.assertEqual(3, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=TIGHT_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        for inst in TIGHT_TOPOLOGY.instances[:2]:
            action = self._assert_action(
                actions,
                'migrate',
                resource_name=inst.name,
                resource_id=inst.uuid,
                migration_type='live',
            )
            self.assertNotIn(
                'destination_node',
                action['input_parameters'],
                'Migration for %s should not have a destination '
                'when backup has insufficient capacity' % inst.name,
            )

    # Migration-disable parameter tests

    def test_non_active_instances_cold_migrated(self):
        """Baseline: active VMs live-migrate, stopped VMs cold-migrate."""
        self.load_topology(MIXED_STATE_TOPOLOGY)
        actions, _ = self._create_audit_and_get_actions(
            {'maintenance_node': 'compute-1', 'backup_node': 'compute-2'}
        )

        # 1 disable + 5 active migrates + 3 stopped migrates = 9
        self.assertEqual(9, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=MIXED_STATE_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        asserted_live = 0
        asserted_cold = 0
        for inst in MIXED_STATE_TOPOLOGY.instances:
            if inst.state == 'active':
                self._assert_action(
                    actions,
                    'migrate',
                    resource_name=inst.name,
                    resource_id=inst.uuid,
                    migration_type='live',
                    destination_node='compute-2',
                )
                asserted_live += 1

            elif inst.state == 'stopped':
                self._assert_action(
                    actions,
                    'migrate',
                    resource_name=inst.name,
                    resource_id=inst.uuid,
                    migration_type='cold',
                    destination_node='compute-2',
                )
                asserted_cold += 1
        self.assertEqual(5, asserted_live)
        self.assertEqual(3, asserted_cold)

    def test_disable_live_migration(self):
        """With disable_live_migration, active VMs are cold-migrated."""
        self.load_topology(MIXED_STATE_TOPOLOGY)
        actions, _ = self._create_audit_and_get_actions(
            {
                'maintenance_node': 'compute-1',
                'backup_node': 'compute-2',
                'disable_live_migration': True,
            }
        )

        # 1 disable + 8 cold migrates = 9
        self.assertEqual(9, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=MIXED_STATE_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        for inst in MIXED_STATE_TOPOLOGY.instances:
            self._assert_action(
                actions,
                'migrate',
                resource_name=inst.name,
                resource_id=inst.uuid,
                migration_type='cold',
                destination_node='compute-2',
            )

    def test_disable_cold_migration(self):
        """With disable_cold_migration, stopped VMs are skipped."""
        self.load_topology(MIXED_STATE_TOPOLOGY)
        actions, _ = self._create_audit_and_get_actions(
            {
                'maintenance_node': 'compute-1',
                'backup_node': 'compute-2',
                'disable_cold_migration': True,
            }
        )

        # 1 disable + 5 live migrates (stopped VMs skipped) = 6
        self.assertEqual(6, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=MIXED_STATE_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        asserted_live = 0
        for inst in MIXED_STATE_TOPOLOGY.instances:
            if inst.state == 'active':
                self._assert_action(
                    actions,
                    'migrate',
                    resource_name=inst.name,
                    resource_id=inst.uuid,
                    migration_type='live',
                    destination_node='compute-2',
                )
                asserted_live += 1

        self.assertEqual(5, asserted_live)

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(5, len(migrate_actions))

    def test_disable_both_migrations(self):
        """With both disabled, active VMs are stopped, stopped VMs skipped."""
        self.load_topology(MIXED_STATE_TOPOLOGY)
        actions, _ = self._create_audit_and_get_actions(
            {
                'maintenance_node': 'compute-1',
                'backup_node': 'compute-2',
                'disable_live_migration': True,
                'disable_cold_migration': True,
            }
        )

        # 1 disable + 5 stop actions (stopped VMs skipped) = 6
        self.assertEqual(6, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=MIXED_STATE_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        asserted_stop = 0
        for inst in MIXED_STATE_TOPOLOGY.instances:
            if inst.state == 'active':
                self._assert_action(actions, 'stop', resource_id=inst.uuid)
                asserted_stop += 1

        self.assertEqual(5, asserted_stop)

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertEqual(0, len(migrate_actions))

        stop_actions = [a for a in actions if a['action_type'] == 'stop']
        self.assertEqual(5, len(stop_actions))
