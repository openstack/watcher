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

"""Functional tests for host_maintenance strategy with audit scope.

Tests that audit scope (host_aggregates, excluded compute_nodes,
excluded instances) correctly restricts which nodes and instances
the host_maintenance strategy operates on.

Scope is set via an AuditTemplate because the Audit API has
``scope`` as a readonly field (audit.py:106).
"""

from watcher.tests.functional import base
from watcher.tests.functional import topology


SCOPED_TOPOLOGY = (
    topology.ComputeTopology()
    .add_computes(count=3, vcpus=64, memory=131072, disk=2000)
    .add_instances(computes=['compute-1'], count=3, vcpus=2)
    .add_instances(
        computes=['compute-3'], count=1, vcpus=2, name_prefix='vm-dev'
    )
)
SCOPED_TOPOLOGY.aggregates = [
    topology.Aggregate(id=1, name='prod', hosts=['compute-1', 'compute-2']),
    topology.Aggregate(id=2, name='dev', hosts=['compute-3']),
]


class TestHostMaintenanceScoped(base.WatcherFunctionalTestCase):
    """Tests for host_maintenance with audit scope restrictions."""

    COMPUTE_TOPOLOGY = SCOPED_TOPOLOGY

    def setUp(self):
        super().setUp()
        self.flags(migration_max_retries=5, group='nova')
        self.flags(migration_interval=0.1, group='nova')
        self._template_counter = 0

    def _create_scoped_audit_and_get_actions(self, scope, parameters):
        """Create an audit with scope (via template) and return actions.

        Scope must be set on an AuditTemplate because the Audit API
        has ``scope`` as readonly. The audit inherits scope from the
        template.
        """
        self._template_counter += 1
        template_name = 'scoped-hm-%s-%d' % (self.id(), self._template_counter)

        resp = self.admin_api.post(
            '/audit_templates',
            {
                'name': template_name,
                'goal': 'cluster_maintaining',
                'strategy': 'host_maintenance',
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
        resp = self.admin_api.get('/action_plans/%s' % ap_uuid)
        self.assertEqual('RECOMMENDED', resp.json()['state'])

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        actions = resp.json()['actions']

        details = []
        for action in actions:
            detail = self.admin_api.get('/actions/%s' % action['uuid']).json()
            details.append(detail)
        return details

    def _create_scoped_audit_expect_failed(self, scope, parameters):
        """Create an audit with scope that is expected to FAIL.

        Used for negative tests where the maintenance_node is not
        in the scoped model, causing the strategy to raise
        ComputeNodeNotFound.
        """
        self._template_counter += 1
        template_name = 'scoped-hm-%s-%d' % (self.id(), self._template_counter)

        resp = self.admin_api.post(
            '/audit_templates',
            {
                'name': template_name,
                'goal': 'cluster_maintaining',
                'strategy': 'host_maintenance',
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

        self._wait_for_audit_state(audit_uuid, 'FAILED')

    # Scope: host_aggregates include

    def test_scope_host_aggregate_include(self):
        """Only nodes in the "prod" aggregate are visible to the strategy.

        compute-3 (in "dev") and its instance vm-dev-1 should be
        invisible. All 3 instances on compute-1 should migrate to
        compute-2.
        """
        scope = [{'compute': [{'host_aggregates': [{'name': 'prod'}]}]}]

        actions = self._create_scoped_audit_and_get_actions(
            scope=scope,
            parameters={
                'maintenance_node': 'compute-1',
                'backup_node': 'compute-2',
            },
        )

        # 1 disable + 3 live migrations = 4 actions
        self.assertEqual(4, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=SCOPED_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        for inst in SCOPED_TOPOLOGY.instances:
            if inst.host == 'compute-1':
                self._assert_action(
                    actions,
                    'migrate',
                    resource_name=inst.name,
                    resource_id=inst.uuid,
                    migration_type='live',
                    destination_node='compute-2',
                )

    # Scope: exclude compute_node

    def test_scope_exclude_compute_node(self):
        """Excluded compute-2 is removed from the model entirely.

        With compute-2 excluded, the strategy cannot use it as a
        backup. Migrations should have no destination_node
        (nova-scheduler decides).
        """
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {'exclude': [{'compute_nodes': [{'name': 'compute-2'}]}]},
                ]
            }
        ]

        actions = self._create_scoped_audit_and_get_actions(
            scope=scope, parameters={'maintenance_node': 'compute-1'}
        )

        # 1 disable + 3 live migrations = 4 actions
        self.assertEqual(4, len(actions))

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=SCOPED_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        for inst in SCOPED_TOPOLOGY.instances:
            if inst.host == 'compute-1':
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
                    'when compute-2 is excluded from scope' % inst.name,
                )

    # Scope: exclude instance

    def test_scope_exclude_instance(self):
        """Excluded instance vm-1 should not be migrated.

        The scope excludes vm-1 by UUID, which sets watcher_exclude=True
        on the instance. A correct strategy should skip it.

        Bug #2154805: host_maintenance does NOT check watcher_exclude,
        so vm-1 is still migrated. The commented-out assertions show
        the expected correct behavior.
        """
        excluded_uuid = SCOPED_TOPOLOGY.instances[0].uuid

        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {'exclude': [{'instances': [{'uuid': excluded_uuid}]}]},
                ]
            }
        ]

        actions = self._create_scoped_audit_and_get_actions(
            scope=scope,
            parameters={
                'maintenance_node': 'compute-1',
                'backup_node': 'compute-2',
            },
        )

        self._assert_action(
            actions,
            'change_nova_service_state',
            resource_name='compute-1',
            resource_id=SCOPED_TOPOLOGY.compute_nodes[0].uuid,
            state='disabled',
        )

        # vm-2 and vm-3 should always be migrated
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-2',
            resource_id=SCOPED_TOPOLOGY.instances[1].uuid,
            migration_type='live',
            destination_node='compute-2',
        )
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-3',
            resource_id=SCOPED_TOPOLOGY.instances[2].uuid,
            migration_type='live',
            destination_node='compute-2',
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']

        # TODO(amoralej) uncomment when bug #2154805 is fixed
        # self.assertEqual(2, len(migrate_actions))
        # self.assertEqual(3, len(actions))
        self.assertEqual(3, len(migrate_actions))
        self.assertEqual(4, len(actions))
        self._assert_action(
            actions,
            'migrate',
            resource_name='vm-1',
            resource_id=excluded_uuid,
            migration_type='live',
            destination_node='compute-2',
        )

    # Negative: maintenance_node not in included aggregate

    def test_scope_maintenance_node_not_in_aggregate(self):
        """maintenance_node outside scope causes audit FAILED.

        Scope includes only "prod" aggregate, but maintenance_node
        is compute-3 (in "dev"). The scoped model removes compute-3,
        so the strategy cannot find it and raises ComputeNodeNotFound.
        The Audit finishes in FAILED state.
        """
        scope = [{'compute': [{'host_aggregates': [{'name': 'prod'}]}]}]

        self._create_scoped_audit_expect_failed(
            scope=scope, parameters={'maintenance_node': 'compute-3'}
        )

    # Negative: maintenance_node is excluded

    def test_scope_maintenance_node_excluded(self):
        """maintenance_node in exclude list causes audit FAILED.

        Scope includes all aggregates but excludes compute-1.
        Setting maintenance_node=compute-1 means the strategy cannot
        find it in the scoped model and raises ComputeNodeNotFound.
        The Audit finishes in FAILED state.
        """
        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': '*'}]},
                    {'exclude': [{'compute_nodes': [{'name': 'compute-1'}]}]},
                ]
            }
        ]

        self._create_scoped_audit_expect_failed(
            scope=scope, parameters={'maintenance_node': 'compute-1'}
        )
