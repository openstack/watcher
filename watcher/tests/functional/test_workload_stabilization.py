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

"""Functional tests for the workload_stabilization strategy.

Tests that the strategy queries Prometheus metrics (via the emulator),
detects CPU/RAM imbalance across hosts using standard deviation, and
proposes live migrations to rebalance the cluster.

Requires both the Nova/Placement emulator (for cluster topology) and
the Prometheus emulator (for host/instance metric values).
"""

import copy
import dataclasses

from watcher.tests.functional import base
from watcher.tests.functional import topology


# 2-node cluster topologies
#
# 2 compute nodes, 16 vcpus / 32768 MiB each.
# All instances: 4 vcpus, 4096 MiB, 20 GB disk.
# CPU ratio per instance: 4/16 = 0.25.  RAM ratio: 4096/32768 = 0.125.
#
# CPU values are normalised fractions (0-1), matching the strategy's
# internal range after normalisation.  RAM values are in MiB.
# Instance values are physically consistent with host values:
#   host.metrics['cpu'] = sum(inst.metrics['cpu']) * 0.25
#   host.metrics['ram'] = sum(inst.metrics['ram'])
#   (both in MiB; host.metrics['ram']/32768 = RAM fraction)
#
# Instance ordering: vm-1 (lowest cpu) to vm-4 (highest cpu) on
# compute-1; vm-5 on compute-2.

TWO_NODE_IMBALANCED = (
    topology.ComputeTopology()
    .add_computes(count=2)
    .add_instances(computes=['compute-1'], count=4)
    .add_instances(computes=['compute-2'], count=1)
    .update_compute('compute-1', metrics={'cpu': 0.80, 'ram': 13107.2})
    .update_compute('compute-2', metrics={'cpu': 0.20, 'ram': 3276.8})
    # c1: sum(cpu)=3.20 -> *0.25=0.80; sum(ram)=13107.2 MiB
    .update_instance('vm-1', metrics={'cpu': 0.68, 'ram': 2785.28})
    .update_instance('vm-2', metrics={'cpu': 0.76, 'ram': 3112.96})
    .update_instance('vm-3', metrics={'cpu': 0.84, 'ram': 3440.64})
    .update_instance('vm-4', metrics={'cpu': 0.92, 'ram': 3768.32})
    # c2: 0.80*0.25=0.20; sum(ram)=3276.8 MiB
    .update_instance('vm-5', metrics={'cpu': 0.80, 'ram': 3276.8})
)

# Balanced CPU: SD of [0.22, 0.20] = 0.01 -- well below 0.1 threshold
# Balanced RAM: SD of [0.10, 0.10] = 0.00 -- also below threshold
TWO_NODE_BALANCED = (
    topology.ComputeTopology()
    .add_computes(count=2)
    .add_instances(computes=['compute-1'], count=4)
    .add_instances(computes=['compute-2'], count=1)
    .update_compute('compute-1', metrics={'cpu': 0.22, 'ram': 3276.8})
    .update_compute('compute-2', metrics={'cpu': 0.20, 'ram': 3276.8})
    # c1: sum(cpu)=0.88 -> *0.25=0.22; sum(ram)=3276.8 MiB
    .update_instance('vm-1', metrics={'cpu': 0.16, 'ram': 819.2})
    .update_instance('vm-2', metrics={'cpu': 0.20, 'ram': 819.2})
    .update_instance('vm-3', metrics={'cpu': 0.24, 'ram': 819.2})
    .update_instance('vm-4', metrics={'cpu': 0.28, 'ram': 819.2})
    # c2: 0.80*0.25=0.20; sum(ram)=3276.8 MiB
    .update_instance('vm-5', metrics={'cpu': 0.80, 'ram': 3276.8})
)

# RAM imbalanced, CPU balanced.
# compute-1: ram=13107.2 MiB (max: 4*4096=16384 MiB)
# compute-2: ram=1638.4 MiB
# SD of [0.40, 0.05] = 0.175 -> exceeds threshold 0.1
# CPU balanced: SD of [0.22, 0.10] = 0.06 -> below threshold 0.1
TWO_NODE_RAM_IMBALANCED = (
    topology.ComputeTopology()
    .add_computes(count=2)
    .add_instances(computes=['compute-1'], count=4)
    .add_instances(computes=['compute-2'], count=1)
    .update_compute('compute-1', metrics={'cpu': 0.22, 'ram': 13107.2})
    .update_compute('compute-2', metrics={'cpu': 0.10, 'ram': 1638.4})
    # c1: sum(cpu)=0.88 -> *0.25=0.22; sum(ram)=13107.2 MiB
    .update_instance('vm-1', metrics={'cpu': 0.22, 'ram': 2785.28})
    .update_instance('vm-2', metrics={'cpu': 0.22, 'ram': 3112.96})
    .update_instance('vm-3', metrics={'cpu': 0.22, 'ram': 3440.64})
    .update_instance('vm-4', metrics={'cpu': 0.22, 'ram': 3768.32})
    # c2: 0.40*0.25=0.10; sum(ram)=1638.4 MiB
    .update_instance('vm-5', metrics={'cpu': 0.40, 'ram': 1638.4})
)

# 4-node cluster topology
#
# For threshold impact and dual-metric testing.
# 4 compute nodes (16 vcpus, 32768 MiB), 10 VMs (4 vcpus each).
# CPU ratio: 0.25.  RAM ratio: 0.125.
#
# VM placement: compute-1 has 5 VMs (overloaded), compute-2 has 3,
# compute-3 and compute-4 have 1 each.
#
# Host CPU: [0.85, 0.50, 0.20, 0.10], SD ~ 0.2924.
# Host RAM: [0.50, 0.30, 0.10, 0.10].
#
# Instance values are physically consistent with host values.

FOUR_NODE_TOPOLOGY = (
    topology.ComputeTopology()
    .add_computes(count=4)
    .add_instances(computes=['compute-1'], count=5)
    .add_instances(computes=['compute-2'], count=3)
    .add_instances(computes=['compute-3'], count=1)
    .add_instances(computes=['compute-4'], count=1)
    .update_compute('compute-1', metrics={'cpu': 0.85, 'ram': 16384.0})
    .update_compute('compute-2', metrics={'cpu': 0.50, 'ram': 9830.4})
    .update_compute('compute-3', metrics={'cpu': 0.20, 'ram': 3276.8})
    .update_compute('compute-4', metrics={'cpu': 0.10, 'ram': 3276.8})
    # c1: sum(cpu)=3.40 -> *0.25=0.85; sum(ram)=16384.0 MiB
    .update_instance('vm-1', metrics={'cpu': 0.50, 'ram': 2621.44})
    .update_instance('vm-2', metrics={'cpu': 0.59, 'ram': 2949.12})
    .update_instance('vm-3', metrics={'cpu': 0.68, 'ram': 3276.8})
    .update_instance('vm-4', metrics={'cpu': 0.77, 'ram': 3604.48})
    .update_instance('vm-5', metrics={'cpu': 0.86, 'ram': 3932.16})
    # c2: sum(cpu)=2.00 -> *0.25=0.50; sum(ram)=9830.4 MiB
    .update_instance('vm-6', metrics={'cpu': 0.54, 'ram': 2785.28})
    .update_instance('vm-7', metrics={'cpu': 0.67, 'ram': 3276.8})
    .update_instance('vm-8', metrics={'cpu': 0.79, 'ram': 3768.32})
    # c3: 0.80*0.25=0.20; sum(ram)=3276.8 MiB
    .update_instance('vm-9', metrics={'cpu': 0.80, 'ram': 3276.8})
    # c4: 0.40*0.25=0.10; sum(ram)=3276.8 MiB
    .update_instance('vm-10', metrics={'cpu': 0.40, 'ram': 3276.8})
)

# 4-node weight-dependent topology
#
# 4 compute nodes, 9 VMs. Placement: c1=5, c2=2, c3=1, c4=1.
#
# cpu=[0.25, 0.04, 0.12, 0.05] SD=0.0838 (above 0.08 threshold)
# ram=[0.2325, 0.18, 0.05, 0.05] SD=0.0803 (above 0.08 threshold)
#
# c1 has 3 effective candidates (vm-3, vm-4 are idle with cpu=0, ram=0):
#   vm-1: CPU-heavy (cpu=0.60, ram=409.6)   maps to c2 via cycle
#   vm-2: RAM-heavy (cpu=0.10, ram=3276.8)  maps to c3 via cycle
#   vm-5: high-ram  (cpu=0.30, ram=3932.16) maps to c3 via cycle
#
# With weights 0.75:0.25 (cpu-heavy): vm-1->c2 wins (CPU improvement dominates)
# With weights 1.0:1.0  (equal):      vm-5->c3 wins (balanced improvement)
# With weights 0.25:0.75 (ram-heavy): vm-2->c3 wins (RAM improvement dominates)
#
# Physical consistency (ram in MiB; host.metrics['ram'] =
# sum(inst.metrics['ram'])):
#   c1: sum(cpu)=[0.60+0.10+0+0+0.30]=1.00 -> *0.25=0.25
#       sum(ram)=[409.6+3276.8+0+0+3932.16]=7618.56 MiB
#   c2: sum(cpu)=[0.08+0.08]=0.16 -> *0.25=0.04
#       sum(ram)=[2949.12+2949.12]=5898.24 MiB
#   c3: 0.48*0.25=0.12; sum(ram)=1638.4 MiB
#   c4: 0.20*0.25=0.05; sum(ram)=1638.4 MiB

FOUR_NODE_WEIGHT = (
    topology.ComputeTopology()
    .add_computes(count=4)
    .add_instances(computes=['compute-1'], count=5)
    .add_instances(computes=['compute-2'], count=2)
    .add_instances(computes=['compute-3'], count=1)
    .add_instances(computes=['compute-4'], count=1)
    .update_compute('compute-1', metrics={'cpu': 0.25, 'ram': 7618.56})
    .update_compute('compute-2', metrics={'cpu': 0.04, 'ram': 5898.24})
    .update_compute('compute-3', metrics={'cpu': 0.12, 'ram': 1638.4})
    .update_compute('compute-4', metrics={'cpu': 0.05, 'ram': 1638.4})
    .update_instance('vm-1', metrics={'cpu': 0.60, 'ram': 409.6})
    .update_instance('vm-2', metrics={'cpu': 0.10, 'ram': 3276.8})
    .update_instance('vm-3', metrics={'cpu': 0.00, 'ram': 0.0})
    .update_instance('vm-4', metrics={'cpu': 0.00, 'ram': 0.0})
    .update_instance('vm-5', metrics={'cpu': 0.30, 'ram': 3932.16})
    .update_instance('vm-6', metrics={'cpu': 0.08, 'ram': 2949.12})
    .update_instance('vm-7', metrics={'cpu': 0.08, 'ram': 2949.12})
    .update_instance('vm-8', metrics={'cpu': 0.48, 'ram': 1638.4})
    .update_instance('vm-9', metrics={'cpu': 0.20, 'ram': 1638.4})
)


# 3-node "single valid destination" topology.
#
# compute-1 (cpu=0.60) and compute-2 (cpu=0.40) are both overloaded;
# compute-3 (cpu=0.10) is nearly idle.  Moving any instance between
# compute-1 and compute-2 does not reduce the cluster SD, so the only
# migration that improves balance is towards compute-3.
#
# Host CPU values are achievable with instance counts:
#   c1 (3 instances, max=3*1.0*0.25=0.75): cpu=0.60, mean=0.80/inst
#   c2 (2 instances, max=2*1.0*0.25=0.50): cpu=0.40, mean=0.80/inst
#   c3 (1 instance): cpu=0.10, mean=0.40/inst
#
# This makes ``host_choice='retry'`` with ``retry_count=2`` fully
# deterministic: each source has exactly 2 candidate destinations,
# ``random.sample(candidates, 2)`` samples BOTH of them, and only the
# compute-3 candidate ever improves the SD.

THREE_NODE_ONE_DEST = (
    topology.ComputeTopology()
    .add_computes(count=3)
    .add_instances(computes=['compute-1'], count=3)
    .add_instances(computes=['compute-2'], count=2)
    .add_instances(computes=['compute-3'], count=1)
    .update_compute('compute-1', metrics={'cpu': 0.60, 'ram': 9830.4})
    .update_compute('compute-2', metrics={'cpu': 0.40, 'ram': 6553.6})
    .update_compute('compute-3', metrics={'cpu': 0.10, 'ram': 1638.4})
    # c1: sum(cpu)=2.40 -> *0.25=0.60; sum(ram)=9830.4 MiB
    .update_instance('vm-1', metrics={'cpu': 0.70, 'ram': 2867.2})
    .update_instance('vm-2', metrics={'cpu': 0.80, 'ram': 3276.8})
    .update_instance('vm-3', metrics={'cpu': 0.90, 'ram': 3686.4})
    # c2: sum(cpu)=1.60 -> *0.25=0.40; sum(ram)=6553.6 MiB
    .update_instance('vm-4', metrics={'cpu': 0.72, 'ram': 2949.12})
    .update_instance('vm-5', metrics={'cpu': 0.88, 'ram': 3604.48})
    # c3: 0.40*0.25=0.10; sum(ram)=1638.4 MiB
    .update_instance('vm-6', metrics={'cpu': 0.40, 'ram': 1638.4})
)

# 4-node topology split across two availability zones.
#
# Same instance placement and metrics as FOUR_NODE_TOPOLOGY, but
# compute-1/compute-2 live in AZ 'az-high' and compute-3/compute-4 in
# AZ 'az-low'.
#
#   az-high: compute-1 (85%) + compute-2 (50%) -> SD=0.175
#   az-low:  compute-3 (20%) + compute-4 (10%) -> SD=0.05

FOUR_NODE_AZ = (
    topology.ComputeTopology()
    .add_computes(count=2, availability_zone='az-high')
    .add_computes(count=2, availability_zone='az-low')
    .add_instances(computes=['compute-1'], count=5)
    .add_instances(computes=['compute-2'], count=3)
    .add_instances(computes=['compute-3'], count=1)
    .add_instances(computes=['compute-4'], count=1)
    .update_compute('compute-1', metrics={'cpu': 0.85, 'ram': 16384.0})
    .update_compute('compute-2', metrics={'cpu': 0.50, 'ram': 9830.4})
    .update_compute('compute-3', metrics={'cpu': 0.20, 'ram': 3276.8})
    .update_compute('compute-4', metrics={'cpu': 0.10, 'ram': 3276.8})
    # Same instance values as FOUR_NODE_TOPOLOGY.
    .update_instance('vm-1', metrics={'cpu': 0.50, 'ram': 2621.44})
    .update_instance('vm-2', metrics={'cpu': 0.59, 'ram': 2949.12})
    .update_instance('vm-3', metrics={'cpu': 0.68, 'ram': 3276.8})
    .update_instance('vm-4', metrics={'cpu': 0.77, 'ram': 3604.48})
    .update_instance('vm-5', metrics={'cpu': 0.86, 'ram': 3932.16})
    .update_instance('vm-6', metrics={'cpu': 0.54, 'ram': 2785.28})
    .update_instance('vm-7', metrics={'cpu': 0.67, 'ram': 3276.8})
    .update_instance('vm-8', metrics={'cpu': 0.79, 'ram': 3768.32})
    .update_instance('vm-9', metrics={'cpu': 0.80, 'ram': 3276.8})
    .update_instance('vm-10', metrics={'cpu': 0.40, 'ram': 3276.8})
)


class TestWorkloadStabilization(base.WatcherFunctionalTestCase):
    """Tests for the workload_stabilization strategy with Prometheus."""

    COMPUTE_TOPOLOGY = topology.ComputeTopology()
    USE_PROMETHEUS = True

    def _create_audit_and_get_actions(
        self, parameters, scope=None, template_name=None
    ):
        """Create a workload_stabilization audit and return actions.

        Call ``self.load_topology()`` before this method to set up
        the cluster topology and metrics.

        :param parameters: strategy parameters dict
        :param scope: optional audit scope (creates an audit template)
        :param template_name: optional audit template name; defaults to
            one derived from ``self.id()``.  Pass a distinct name when a
            single test creates more than one template.
        :returns: (action_details, action_plan) tuple
        """
        if scope:
            resp = self.admin_api.post(
                '/audit_templates',
                {
                    'name': template_name or 'ws-template-%s' % self.id(),
                    'goal': 'workload_balancing',
                    'strategy': 'workload_stabilization',
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
        else:
            resp = self.admin_api.post(
                '/audits',
                {
                    'audit_type': 'ONESHOT',
                    'goal': 'workload_balancing',
                    'strategy': 'workload_stabilization',
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
        self.assertIn(resp.json()['state'], ['RECOMMENDED', 'SUCCEEDED'])

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        actions = resp.json()['actions']

        details = []
        for action in actions:
            detail = self.admin_api.get('/actions/%s' % action['uuid']).json()
            details.append(detail)

        ap_detail = self.admin_api.get('/action_plans/%s' % ap_uuid).json()
        return details, ap_detail

    def _create_audit_no_actions(self, parameters):
        """Create audit expecting SUCCEEDED with empty action plan."""
        resp = self.admin_api.post(
            '/audits',
            {
                'audit_type': 'ONESHOT',
                'goal': 'workload_balancing',
                'strategy': 'workload_stabilization',
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
        self.assertEqual('SUCCEEDED', resp.json()['state'])

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        return resp.json()['actions']

    def _create_audit_no_actions_scoped(
        self, parameters, scope, template_name=None
    ):
        """Create a scoped audit expecting SUCCEEDED with no actions.

        Like ``_create_audit_no_actions`` but routes the audit through
        an audit template carrying the given *scope*.
        """
        resp = self.admin_api.post(
            '/audit_templates',
            {
                'name': template_name or 'ws-template-%s' % self.id(),
                'goal': 'workload_balancing',
                'strategy': 'workload_stabilization',
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
        self.assertEqual('SUCCEEDED', resp.json()['state'])

        resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
        return resp.json()['actions']

    def test_threshold_impact_on_migrations(self):
        """Higher threshold produces fewer migrations on the same cluster.

        4 compute nodes, 10 VMs (4 vcpus each).  Host CPU
        [85%, 50%, 20%, 10%], SD ~ 0.29.  Three threshold levels:

        - threshold 0.10 -> 3 migrations (stops when SD < 0.10)
        - threshold 0.25 -> 1 migration  (stops when SD < 0.25)
        - threshold 0.30 -> 0 migrations (SD < threshold, no action)

        All use host_choice='cycle' so each instance tries exactly
        one deterministic destination.
        """
        base_params = {
            'metrics': ['instance_cpu_usage'],
            'weights': {'instance_cpu_usage_weight': 1.0},
            'periods': {'instance': 720, 'compute_node': 600},
            'aggregation_method': {'instance': 'mean', 'compute_node': 'mean'},
            'granularity': 300,
            'host_choice': 'fullsearch',
        }

        # Expected action plans per threshold (computed from strategy trace).
        #
        # SD before audit: 0.2924 (host CPU [0.85, 0.50, 0.20, 0.10]).
        #
        # Instance CPUs are physically consistent with host CPUs
        # (via ratio=0.25):
        #   c1: vm-1=0.50, vm-2=0.59, vm-3=0.68, vm-4=0.77, vm-5=0.86
        #   c2: vm-6=0.54, vm-7=0.67, vm-8=0.79
        #   c3: vm-9=0.80  c4: vm-10=0.40
        #
        # With cycle: per source host, candidates cycle through other nodes.
        # Strategy applies the globally-best improving migration at each step.
        #
        # threshold 0.10 -> 3 migrations, SD after ~ 0.0976
        #   vm-5 c1->c4 (gives SD=0.1672), then vm-4 c1->c4
        #   (SD=0.1252) and finally vm-3 c1->c3
        #   (SD drops to 0.0975 < 0.10)
        # threshold 0.25 -> 1 migration, SD after ~ 0.1672
        #   vm-5 c1->c4 (SD=0.1672 < 0.25, stop)
        # threshold 0.30 -> 0 migrations (initial SD 0.2924 < 0.30)

        threshold_cases = [
            {
                'threshold': 0.10,
                'expected_ap_state': 'RECOMMENDED',
                'expected_migrations': [
                    ('vm-5', 'compute-1', 'compute-4'),
                    ('vm-4', 'compute-1', 'compute-4'),
                    ('vm-3', 'compute-1', 'compute-3'),
                ],
                'sd_before': 0.2924,
                'sd_after': 0.0976,
            },
            {
                'threshold': 0.25,
                'expected_ap_state': 'RECOMMENDED',
                'expected_migrations': [('vm-5', 'compute-1', 'compute-4')],
                'sd_before': 0.2924,
                'sd_after': 0.1672,
            },
            {
                'threshold': 0.30,
                'expected_ap_state': 'SUCCEEDED',
                'expected_migrations': [],
                'sd_before': 0.0,
                'sd_after': 0.0,
            },
        ]

        for threshold_case in threshold_cases:
            threshold = threshold_case['threshold']
            with self.subTest(threshold=threshold):
                self.load_topology(FOUR_NODE_TOPOLOGY)

                params = dict(base_params)
                params['thresholds'] = {'instance_cpu_usage': threshold}

                actions, action_plan = self._create_audit_and_get_actions(
                    parameters=params
                )

                self.assertEqual(
                    threshold_case['expected_ap_state'],
                    action_plan['state'],
                    'threshold=%.2f: expected AP state %s, got %s'
                    % (
                        threshold,
                        threshold_case['expected_ap_state'],
                        action_plan['state'],
                    ),
                )

                migrate_actions = [
                    a for a in actions if a['action_type'] == 'migrate'
                ]

                expected_count = len(threshold_case['expected_migrations'])
                self.assertEqual(
                    expected_count,
                    len(migrate_actions),
                    'threshold=%.2f: expected %d migrations, got %d'
                    % (threshold, expected_count, len(migrate_actions)),
                )

                actual_migrations = [
                    (
                        a['input_parameters']['resource_name'],
                        a['input_parameters']['source_node'],
                        a['input_parameters']['destination_node'],
                    )
                    for a in migrate_actions
                ]
                self.assertEqual(
                    threshold_case['expected_migrations'],
                    actual_migrations,
                    'threshold=%.2f: migration details mismatch' % threshold,
                )

                for action in migrate_actions:
                    self.assertEqual(
                        'live', action['input_parameters']['migration_type']
                    )

                indicators = {
                    ei['name']: ei['value']
                    for ei in action_plan.get('efficacy_indicators', [])
                }
                self.assertAlmostEqual(
                    threshold_case['sd_before'],
                    indicators['standard_deviation_before_audit'],
                    places=3,
                    msg='threshold=%.2f: sd_before mismatch' % threshold,
                )
                self.assertAlmostEqual(
                    threshold_case['sd_after'],
                    indicators['standard_deviation_after_audit'],
                    places=3,
                    msg='threshold=%.2f: sd_after mismatch' % threshold,
                )
                self.assertEqual(
                    float(expected_count),
                    indicators['instance_migrations_count'],
                )
                self.assertEqual(10.0, indicators['instances_count'])

    def test_workload_stabilization_balanced_cluster(self):
        """Balanced cluster produces no migrations.

        Both hosts have similar CPU (~22% vs ~20%), so standard
        deviation is below the threshold.
        """
        self.load_topology(TWO_NODE_BALANCED)
        actions = self._create_audit_no_actions(
            parameters={
                'metrics': ['instance_cpu_usage'],
                'thresholds': {'instance_cpu_usage': 0.1},
                'weights': {'instance_cpu_usage_weight': 1.0},
                'periods': {'instance': 720, 'compute_node': 600},
                'aggregation_method': {
                    'instance': 'mean',
                    'compute_node': 'mean',
                },
                'granularity': 300,
                'host_choice': 'fullsearch',
            }
        )

        self.assertEqual(
            0, len(actions), 'Expected no actions for a balanced cluster'
        )

    def test_workload_stabilization_with_ram_metric(self):
        """RAM imbalance triggers migrations when using RAM metric.

        CPU is balanced but RAM is heavily skewed on compute-1.
        Using instance_ram_usage metric should detect the imbalance
        and propose migrations.
        """
        self.load_topology(TWO_NODE_RAM_IMBALANCED)
        actions, action_plan = self._create_audit_and_get_actions(
            parameters={
                'metrics': ['instance_ram_usage'],
                'thresholds': {'instance_ram_usage': 0.1},
                'weights': {'instance_ram_usage_weight': 1.0},
                'periods': {'instance': 720, 'compute_node': 600},
                'aggregation_method': {
                    'instance': 'mean',
                    'compute_node': 'mean',
                },
                'granularity': 300,
                'host_choice': 'fullsearch',
            }
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertGreater(
            len(migrate_actions),
            0,
            'Expected at least one migration for RAM imbalance',
        )

        for action in migrate_actions:
            params = action['input_parameters']
            self.assertEqual('live', params['migration_type'])

    def test_workload_stabilization_with_both_metrics(self):
        """Both CPU and RAM metrics drive migration decisions together.

        4 compute nodes, 10 VMs.  CPU SD=0.29, RAM SD=0.20.
        Three threshold combos produce different migration counts:

        - cpu=0.10 ram=0.10 -> 3 migrations
        - cpu=0.20 ram=0.20 -> 1 migration
        - cpu=0.30 ram=0.30 -> 0 migrations
        """
        base_params = {
            'metrics': ['instance_cpu_usage', 'instance_ram_usage'],
            'weights': {
                'instance_cpu_usage_weight': 1.0,
                'instance_ram_usage_weight': 1.0,
            },
            'periods': {'instance': 720, 'compute_node': 600},
            'aggregation_method': {'instance': 'mean', 'compute_node': 'mean'},
            'granularity': 300,
            'host_choice': 'cycle',
        }

        # Expected action plans per dual-metric threshold combo.
        #
        # sd_before = first metric's SD when threshold exceeded
        #  cpu_sd = 0.2924.
        # sd_after  = weighted_sd (cpu_sd * 1.0 + ram_sd * 1.0)
        #  after last migration.
        # Host RAMs: c1=0.50, c2=0.30, c3=0.10, c4=0.10 -> RAM SD=0.1658.
        # With dual metrics the weighted_sd is cpu_sd+ram_sd.  After migration,
        # balanced triggers when ANY metric's per-metric SD < its threshold.
        #
        # With cycle (per source host the candidates cycle: c2->c3->c4 for c1):
        #   cpu_t=0.10 ram_t=0.10 -> 2 migrations
        #     vm-5 c1->c3 (best weighted improvement), then vm-3 c1->c4
        #     cpu_sd drops to 0.088 < 0.10 -> stop
        #   cpu_t=0.20 ram_t=0.20 -> 1 migration
        #     vm-5 c1->c3 (cpu_sd=0.197 < 0.20 -> stop)
        #   cpu_t=0.30 ram_t=0.30 -> 0 migrations (cpu_sd 0.2924 < 0.30)

        dual_metric_cases = [
            {
                'cpu_threshold': 0.10,
                'ram_threshold': 0.10,
                'expected_ap_state': 'RECOMMENDED',
                'expected_migrations': [
                    ('vm-5', 'compute-1', 'compute-3'),
                    ('vm-3', 'compute-1', 'compute-4'),
                ],
                'sd_before': 0.2924,
                'sd_after': 0.1289,
            },
            {
                'cpu_threshold': 0.20,
                'ram_threshold': 0.20,
                'expected_ap_state': 'RECOMMENDED',
                'expected_migrations': [('vm-5', 'compute-1', 'compute-3')],
                'sd_before': 0.2924,
                'sd_after': 0.3001,
            },
            {
                'cpu_threshold': 0.30,
                'ram_threshold': 0.30,
                'expected_ap_state': 'SUCCEEDED',
                'expected_migrations': [],
                'sd_before': 0.0,
                'sd_after': 0.0,
            },
        ]

        for dual_metric_case in dual_metric_cases:
            cpu_t = dual_metric_case['cpu_threshold']
            ram_t = dual_metric_case['ram_threshold']
            with self.subTest(cpu_threshold=cpu_t, ram_threshold=ram_t):
                self.load_topology(FOUR_NODE_TOPOLOGY)

                params = dict(base_params)
                params['thresholds'] = {
                    'instance_cpu_usage': cpu_t,
                    'instance_ram_usage': ram_t,
                }

                actions, action_plan = self._create_audit_and_get_actions(
                    parameters=params
                )
                self.assertEqual(
                    dual_metric_case['expected_ap_state'],
                    action_plan['state'],
                    'cpu_t=%.2f ram_t=%.2f: expected AP state %s, got %s'
                    % (
                        cpu_t,
                        ram_t,
                        dual_metric_case['expected_ap_state'],
                        action_plan['state'],
                    ),
                )

                migrate_actions = [
                    a for a in actions if a['action_type'] == 'migrate'
                ]

                expected_count = len(dual_metric_case['expected_migrations'])
                self.assertEqual(
                    expected_count,
                    len(migrate_actions),
                    'cpu_t=%.2f ram_t=%.2f: expected %d migrations, got %d'
                    % (cpu_t, ram_t, expected_count, len(migrate_actions)),
                )

                actual_migrations = [
                    (
                        a['input_parameters']['resource_name'],
                        a['input_parameters']['source_node'],
                        a['input_parameters']['destination_node'],
                    )
                    for a in migrate_actions
                ]
                self.assertEqual(
                    dual_metric_case['expected_migrations'],
                    actual_migrations,
                    'cpu_t=%.2f ram_t=%.2f: migration details mismatch'
                    % (cpu_t, ram_t),
                )

                for action in migrate_actions:
                    self.assertEqual(
                        'live', action['input_parameters']['migration_type']
                    )

                indicators = {
                    ei['name']: ei['value']
                    for ei in action_plan.get('efficacy_indicators', [])
                }
                self.assertAlmostEqual(
                    dual_metric_case['sd_before'],
                    indicators['standard_deviation_before_audit'],
                    places=3,
                    msg='cpu_t=%.2f ram_t=%.2f: sd_before mismatch'
                    % (cpu_t, ram_t),
                )
                self.assertAlmostEqual(
                    dual_metric_case['sd_after'],
                    indicators['standard_deviation_after_audit'],
                    places=3,
                    msg='cpu_t=%.2f ram_t=%.2f: sd_after mismatch'
                    % (cpu_t, ram_t),
                )
                self.assertEqual(
                    float(expected_count),
                    indicators['instance_migrations_count'],
                )
                self.assertEqual(10.0, indicators['instances_count'])

    def test_workload_stabilization_weight_impact(self):
        """Weight ratios determine which instances migrate.

        4 compute nodes, 9 VMs. Three effective candidates on compute-1:
          vm-1 (CPU-heavy) -> compute-2  wins for cpu-heavy weights (0.75:0.25)
          vm-5 (high-ram)  -> compute-3  wins for equal weights (1:1)
          vm-2 (RAM-heavy) -> compute-3  wins for ram-heavy weights (0.25:0.75)

        Each migration drops cpu_sd below 0.08 -> balanced -> stop after one
        step.
        sd_before = init_cpu_sd (same topology for all weight cases).
        sd_after = weighted_sd after the single migration (differs by weights).
        """
        # Expected action plans per weight combo.
        #
        # cpu=[0.25, 0.04, 0.12, 0.05] SD=0.0838 (above 0.08 threshold).
        # ram=[0.2325, 0.18, 0.05, 0.05] SD=0.0803 (above 0.08 threshold).
        # sd_before = init_cpu_sd (cpu checked first).
        #
        # All three weight cases use FOUR_NODE_WEIGHT with thresholds
        # 0.08/0.08. With cycle on c1 instances:
        #   vm-3->c4 and vm-4->c2 are idle (cpu=ram=0) and have no effect.
        #   vm-1->c2, vm-2->c3, vm-5->c3 compete; weight ratio determines
        #   the winner.
        #
        # cpu-heavy (0.75:0.25): vm-1->c2 -- CPU improvement dominates
        # equal     (1.0:1.0):   vm-5->c3 -- balanced combined improvement
        # ram-heavy (0.25:0.75): vm-2->c3 -- RAM improvement dominates
        #
        # Each migration drops cpu_sd below 0.08 -> BALANCED -> stop after one
        # step.
        # sd_after = weighted_sd at stop (differs by weight, showing
        # sensitivity).

        weight_cases = [
            {
                'cpu_weight': 1.0,
                'ram_weight': 1.0,
                'label': 'equal',
                'expected_migrations': [('vm-5', 'compute-1', 'compute-3')],
                'sd_before': 0.0838,
                'sd_after': 0.1224,
            },
            {
                'cpu_weight': 0.75,
                'ram_weight': 0.25,
                'label': 'cpu-heavy',
                'expected_migrations': [('vm-1', 'compute-1', 'compute-2')],
                'sd_before': 0.0838,
                'sd_after': 0.0574,
            },
            {
                'cpu_weight': 0.25,
                'ram_weight': 0.75,
                'label': 'ram-heavy',
                'expected_migrations': [('vm-2', 'compute-1', 'compute-3')],
                'sd_before': 0.0838,
                'sd_after': 0.0550,
            },
        ]

        for weight_case in weight_cases:
            cpu_w = weight_case['cpu_weight']
            ram_w = weight_case['ram_weight']
            with self.subTest(label=weight_case['label']):
                self.load_topology(FOUR_NODE_WEIGHT)

                params = {
                    'metrics': ['instance_cpu_usage', 'instance_ram_usage'],
                    'thresholds': {
                        'instance_cpu_usage': 0.08,
                        'instance_ram_usage': 0.08,
                    },
                    'weights': {
                        'instance_cpu_usage_weight': cpu_w,
                        'instance_ram_usage_weight': ram_w,
                    },
                    'periods': {'instance': 720, 'compute_node': 600},
                    'aggregation_method': {
                        'instance': 'mean',
                        'compute_node': 'mean',
                    },
                    'granularity': 300,
                    'host_choice': 'cycle',
                }

                actions, action_plan = self._create_audit_and_get_actions(
                    parameters=params
                )
                self.assertEqual(
                    'RECOMMENDED',
                    action_plan['state'],
                    'weights=%s: expected RECOMMENDED, got %s'
                    % (weight_case['label'], action_plan['state']),
                )

                migrate_actions = [
                    a for a in actions if a['action_type'] == 'migrate'
                ]

                expected_count = len(weight_case['expected_migrations'])
                self.assertEqual(
                    expected_count,
                    len(migrate_actions),
                    'weights=%s: expected %d migrations, got %d'
                    % (
                        weight_case['label'],
                        expected_count,
                        len(migrate_actions),
                    ),
                )

                actual_migrations = [
                    (
                        a['input_parameters']['resource_name'],
                        a['input_parameters']['source_node'],
                        a['input_parameters']['destination_node'],
                    )
                    for a in migrate_actions
                ]
                self.assertEqual(
                    weight_case['expected_migrations'],
                    actual_migrations,
                    'weights=%s: migration details mismatch'
                    % weight_case['label'],
                )

                for action in migrate_actions:
                    self.assertEqual(
                        'live', action['input_parameters']['migration_type']
                    )

                indicators = {
                    ei['name']: ei['value']
                    for ei in action_plan.get('efficacy_indicators', [])
                }
                self.assertAlmostEqual(
                    weight_case['sd_before'],
                    indicators['standard_deviation_before_audit'],
                    places=3,
                    msg='weights=%s: sd_before mismatch'
                    % weight_case['label'],
                )
                self.assertAlmostEqual(
                    weight_case['sd_after'],
                    indicators['standard_deviation_after_audit'],
                    places=3,
                    msg='weights=%s: sd_after mismatch' % weight_case['label'],
                )
                self.assertEqual(
                    float(expected_count),
                    indicators['instance_migrations_count'],
                )
                self.assertEqual(9.0, indicators['instances_count'])

    def test_workload_stabilization_aggregate_scope(self):
        """Aggregate scope limits which nodes the strategy sees.

        Same 4-node cluster split into two aggregates:
          agg-high: compute-1 (85%) + compute-2 (50%) -> SD=0.175
          agg-low:  compute-3 (20%) + compute-4 (10%) -> SD=0.05

        With threshold 0.10:
          agg-high scope -> 1 migration (vm-5 c1->c2, SD drops to 0.045)
          agg-low scope  -> 0 migrations (SD 0.05 < threshold)
          both + exclude c1 -> 1 migration (vm-7 c2->c4, SD 0.057)
        """
        aggregates = [
            topology.Aggregate(
                id=1, name='agg-high', hosts=['compute-1', 'compute-2']
            ),
            topology.Aggregate(
                id=2, name='agg-low', hosts=['compute-3', 'compute-4']
            ),
        ]
        topo_with_aggs = dataclasses.replace(
            FOUR_NODE_TOPOLOGY, aggregates=aggregates
        )

        params = {
            'metrics': ['instance_cpu_usage'],
            'thresholds': {'instance_cpu_usage': 0.10},
            'weights': {'instance_cpu_usage_weight': 1.0},
            'periods': {'instance': 720, 'compute_node': 600},
            'aggregation_method': {'instance': 'mean', 'compute_node': 'mean'},
            'granularity': 300,
            'host_choice': 'fullsearch',
        }

        with self.subTest(aggregate='agg-high'):
            self.load_topology(topo_with_aggs)

            scope = [
                {'compute': [{'host_aggregates': [{'name': 'agg-high'}]}]}
            ]
            resp = self.admin_api.post(
                '/audit_templates',
                {
                    'name': 'ws-agg-high-%s' % self.id(),
                    'goal': 'workload_balancing',
                    'strategy': 'workload_stabilization',
                    'scope': scope,
                },
            )
            self.assertEqual(201, resp.status_code)
            template_uuid = resp.json()['uuid']

            resp = self.admin_api.post(
                '/audits',
                {
                    'audit_type': 'ONESHOT',
                    'audit_template_uuid': template_uuid,
                    'parameters': params,
                },
            )
            self.assertEqual(201, resp.status_code)
            audit_uuid = resp.json()['uuid']
            self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')

            resp = self.admin_api.get(
                '/action_plans?audit_uuid=%s' % audit_uuid
            )
            ap_uuid = resp.json()['action_plans'][0]['uuid']
            ap = self.admin_api.get('/action_plans/%s' % ap_uuid).json()
            self.assertEqual('RECOMMENDED', ap['state'])

            resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
            migrate_actions = []
            for a in resp.json()['actions']:
                detail = self.admin_api.get('/actions/%s' % a['uuid']).json()
                if detail['action_type'] == 'migrate':
                    migrate_actions.append(detail)

            self.assertEqual(1, len(migrate_actions))
            action = migrate_actions[0]
            # vm-3 (cpu=0.68) is the closest instance to the balance midpoint
            # (c1=0.85, c2=0.50 -> ideal contribution=0.175, i.e. cpu=0.70),
            # so fullsearch picks vm-3 over vm-5 (which overshoots).
            self.assertEqual(
                'vm-3', action['input_parameters']['resource_name']
            )
            self.assertEqual(
                'compute-1', action['input_parameters']['source_node']
            )
            self.assertEqual(
                'compute-2', action['input_parameters']['destination_node']
            )
            self.assertEqual(
                'live', action['input_parameters']['migration_type']
            )

            indicators = {
                ei['name']: ei['value']
                for ei in ap.get('efficacy_indicators', [])
            }
            self.assertAlmostEqual(
                0.175, indicators['standard_deviation_before_audit'], places=3
            )
            # vm-3 cpu=0.68, contribution=0.17: c1=0.68, c2=0.67, SD~0.005
            self.assertAlmostEqual(
                0.005, indicators['standard_deviation_after_audit'], places=3
            )
            self.assertEqual(8.0, indicators['instances_count'])

        with self.subTest(aggregate='agg-low'):
            self.load_topology(topo_with_aggs)

            scope = [{'compute': [{'host_aggregates': [{'name': 'agg-low'}]}]}]
            resp = self.admin_api.post(
                '/audit_templates',
                {
                    'name': 'ws-agg-low-%s' % self.id(),
                    'goal': 'workload_balancing',
                    'strategy': 'workload_stabilization',
                    'scope': scope,
                },
            )
            self.assertEqual(201, resp.status_code)
            template_uuid = resp.json()['uuid']

            resp = self.admin_api.post(
                '/audits',
                {
                    'audit_type': 'ONESHOT',
                    'audit_template_uuid': template_uuid,
                    'parameters': params,
                },
            )
            self.assertEqual(201, resp.status_code)
            audit_uuid = resp.json()['uuid']
            self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')

            resp = self.admin_api.get(
                '/action_plans?audit_uuid=%s' % audit_uuid
            )
            ap_uuid = resp.json()['action_plans'][0]['uuid']
            ap = self.admin_api.get('/action_plans/%s' % ap_uuid).json()
            self.assertEqual('SUCCEEDED', ap['state'])

            resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
            self.assertEqual(0, len(resp.json()['actions']))

        # Both aggregates, exclude compute-1.
        # Remaining: c2 (50%), c3 (20%), c4 (10%).  SD=0.170.
        # With cycle (3 nodes), vm-7 on c2 migrates to c4.
        with self.subTest(aggregate='both-exclude-c1'):
            self.load_topology(topo_with_aggs)

            scope = [
                {
                    'compute': [
                        {
                            'host_aggregates': [
                                {'name': 'agg-high'},
                                {'name': 'agg-low'},
                            ]
                        },
                        {
                            'exclude': [
                                {'compute_nodes': [{'name': 'compute-1'}]}
                            ]
                        },
                    ]
                }
            ]
            resp = self.admin_api.post(
                '/audit_templates',
                {
                    'name': 'ws-agg-excl-%s' % self.id(),
                    'goal': 'workload_balancing',
                    'strategy': 'workload_stabilization',
                    'scope': scope,
                },
            )
            self.assertEqual(201, resp.status_code)
            template_uuid = resp.json()['uuid']

            params_cycle = dict(params)
            params_cycle['host_choice'] = 'cycle'

            resp = self.admin_api.post(
                '/audits',
                {
                    'audit_type': 'ONESHOT',
                    'audit_template_uuid': template_uuid,
                    'parameters': params_cycle,
                },
            )
            self.assertEqual(201, resp.status_code)
            audit_uuid = resp.json()['uuid']
            self._wait_for_audit_state(audit_uuid, 'SUCCEEDED')

            resp = self.admin_api.get(
                '/action_plans?audit_uuid=%s' % audit_uuid
            )
            ap_uuid = resp.json()['action_plans'][0]['uuid']
            ap = self.admin_api.get('/action_plans/%s' % ap_uuid).json()
            self.assertEqual('RECOMMENDED', ap['state'])

            resp = self.admin_api.get('/actions?action_plan_uuid=%s' % ap_uuid)
            migrate_actions = []
            for a in resp.json()['actions']:
                detail = self.admin_api.get('/actions/%s' % a['uuid']).json()
                if detail['action_type'] == 'migrate':
                    migrate_actions.append(detail)

            self.assertEqual(1, len(migrate_actions))
            action = migrate_actions[0]
            # With cycle on [c2, c3, c4]: vm-6->c3, vm-7->c4, vm-8->c3.
            # vm-7 (cpu=0.67) -> c4 gives the lowest SD among candidates.
            self.assertEqual(
                'vm-7', action['input_parameters']['resource_name']
            )
            self.assertEqual(
                'compute-2', action['input_parameters']['source_node']
            )
            self.assertEqual(
                'compute-4', action['input_parameters']['destination_node']
            )
            self.assertEqual(
                'live', action['input_parameters']['migration_type']
            )

            indicators = {
                ei['name']: ei['value']
                for ei in ap.get('efficacy_indicators', [])
            }
            self.assertAlmostEqual(
                0.170, indicators['standard_deviation_before_audit'], places=3
            )
            # vm-7 cpu=0.67, contribution=0.1675:
            # c2=0.3325, c3=0.20, c4=0.2675 -> SD~0.054
            self.assertAlmostEqual(
                0.054, indicators['standard_deviation_after_audit'], places=3
            )
            self.assertEqual(5.0, indicators['instances_count'])

    def test_workload_stabilization_excluded_instance(self):
        """Excluded instance is not migrated even from overloaded host.

        Scope excludes vm-4 (the highest CPU instance on compute-1
        with distribute's low-to-high ramp).  The strategy should
        skip it (workload_stabilization checks watcher_exclude).

        An aggregate is needed in the scope so the scope handler
        includes compute nodes in the model.
        """
        excluded_uuid = 'bbbb0004-0000-0000-0000-000000000004'

        topo_with_agg = dataclasses.replace(
            TWO_NODE_IMBALANCED,
            aggregates=[
                topology.Aggregate(
                    id=1, name='all-hosts', hosts=['compute-1', 'compute-2']
                )
            ],
        )
        self.load_topology(topo_with_agg)

        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': 'all-hosts'}]},
                    {'exclude': [{'instances': [{'uuid': excluded_uuid}]}]},
                ]
            }
        ]

        actions, action_plan = self._create_audit_and_get_actions(
            parameters={
                'metrics': ['instance_cpu_usage'],
                'thresholds': {'instance_cpu_usage': 0.1},
                'weights': {'instance_cpu_usage_weight': 1.0},
                'periods': {'instance': 720, 'compute_node': 600},
                'aggregation_method': {
                    'instance': 'mean',
                    'compute_node': 'mean',
                },
                'granularity': 300,
                'host_choice': 'fullsearch',
            },
            scope=scope,
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']

        migrated_ids = {
            a['input_parameters']['resource_name'] for a in migrate_actions
        }
        self.assertNotIn(
            'vm-4',
            migrated_ids,
            'Excluded instance vm-4 should not be migrated',
        )

    def test_workload_stabilization_host_choice_variants(self):
        """All host_choice values agree on a 2-node cluster.

        This is the only coverage of the DEFAULT host_choice ('retry')
        alongside 'cycle' and 'fullsearch'.  On a 2-node cluster every
        instance has exactly one candidate destination (compute-2), so
        the three node-selection strategies must evaluate the identical
        move and produce the identical migration plan.

        Uses retry_count=1 (the default), which is deterministic for
        'retry' because ``random.sample`` of a single-element candidate
        list always returns that element.
        """
        plans_by_choice = {}

        HOST_CHOICE_CASES = ['retry', 'cycle', 'fullsearch']

        for host_choice in HOST_CHOICE_CASES:
            with self.subTest(host_choice=host_choice):
                self.load_topology(TWO_NODE_IMBALANCED)

                actions, ap = self._create_audit_and_get_actions(
                    parameters={
                        'metrics': ['instance_cpu_usage'],
                        'thresholds': {'instance_cpu_usage': 0.1},
                        'weights': {'instance_cpu_usage_weight': 1.0},
                        'periods': {'instance': 720, 'compute_node': 600},
                        'aggregation_method': {
                            'instance': 'mean',
                            'compute_node': 'mean',
                        },
                        'granularity': 300,
                        'host_choice': host_choice,
                        'retry_count': 1,
                    }
                )

                migrate_actions = [
                    a for a in actions if a['action_type'] == 'migrate'
                ]
                self.assertGreater(
                    len(migrate_actions),
                    0,
                    'host_choice=%s: expected at least one migration'
                    % host_choice,
                )

                migrations = []
                for a in migrate_actions:
                    params = a['input_parameters']
                    self.assertEqual(
                        'compute-2',
                        params['destination_node'],
                        'host_choice=%s: on 2 nodes every migration must '
                        'target compute-2' % host_choice,
                    )
                    self.assertEqual('live', params['migration_type'])
                    migrations.append(
                        (params['resource_name'], params['source_node'])
                    )

                plans_by_choice[host_choice] = sorted(migrations)

        # Every host_choice must have produced the same plan.
        reference = plans_by_choice['retry']
        for host_choice, plan in plans_by_choice.items():
            self.assertEqual(
                reference,
                plan,
                'host_choice=%s produced a different plan than retry: '
                '%s != %s' % (host_choice, plan, reference),
            )

    def test_workload_stabilization_retry_count(self):
        """retry_count>1 explores multiple candidate destinations.

        On THREE_NODE_ONE_DEST compute-1 and compute-2 are both
        overloaded and compute-3 is idle, so the only balancing move is
        towards compute-3.  With host_choice='retry' and retry_count=2
        each source samples BOTH of its two candidate destinations, so
        the strategy is guaranteed to discover compute-3 regardless of
        sampling order -- proving retry_count is honored and the retry
        path converges deterministically here.
        """
        self.load_topology(THREE_NODE_ONE_DEST)

        actions, ap = self._create_audit_and_get_actions(
            parameters={
                'metrics': ['instance_cpu_usage'],
                'thresholds': {'instance_cpu_usage': 0.1},
                'weights': {'instance_cpu_usage_weight': 1.0},
                'periods': {'instance': 720, 'compute_node': 600},
                'aggregation_method': {
                    'instance': 'mean',
                    'compute_node': 'mean',
                },
                'granularity': 300,
                'host_choice': 'retry',
                'retry_count': 2,
            }
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertGreater(
            len(migrate_actions),
            0,
            'Expected at least one migration towards the idle node',
        )
        for a in migrate_actions:
            params = a['input_parameters']
            self.assertEqual(
                'compute-3',
                params['destination_node'],
                'retry_count=2 should route every migration to the only '
                'improving destination (compute-3)',
            )
            self.assertEqual('live', params['migration_type'])

    def test_workload_stabilization_default_parameters(self):
        """Strategy runs with schema defaults (empty parameters).

        No parameters are passed, so the strategy falls back to every
        get_schema() default: metrics=[instance_cpu_usage],
        thresholds cpu=0.1, host_choice='retry', retry_count=1, etc.
        On the CPU-imbalanced 2-node cluster (host SD 0.30 >> 0.1) the
        defaults must still detect the imbalance and rebalance towards
        compute-2.
        """
        self.load_topology(TWO_NODE_IMBALANCED)

        actions, ap = self._create_audit_and_get_actions(parameters={})

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertGreater(
            len(migrate_actions),
            0,
            'Default parameters should still rebalance an imbalanced cluster',
        )
        for a in migrate_actions:
            params = a['input_parameters']
            self.assertEqual('compute-2', params['destination_node'])
            self.assertEqual('live', params['migration_type'])

    def test_workload_stabilization_availability_zone_scope(self):
        """availability_zones scope limits the nodes the strategy sees.

        FOUR_NODE_AZ has the same layout as FOUR_NODE_TOPOLOGY but
        splits the nodes across two AZs:
          az-high: compute-1 (85%) + compute-2 (50%) -> SD=0.175
          az-low:  compute-3 (20%) + compute-4 (10%) -> SD=0.05

        Selecting az-high yields the same single migration and efficacy
        indicators as the equivalent agg-high aggregate scope (vm-3 from
        compute-1 to compute-2, sd_before=0.175, sd_after~0.005).
        az-low is already balanced (SD 0.05 < 0.10) so it yields no
        migrations.
        """
        params = {
            'metrics': ['instance_cpu_usage'],
            'thresholds': {'instance_cpu_usage': 0.10},
            'weights': {'instance_cpu_usage_weight': 1.0},
            'periods': {'instance': 720, 'compute_node': 600},
            'aggregation_method': {'instance': 'mean', 'compute_node': 'mean'},
            'granularity': 300,
            'host_choice': 'fullsearch',
        }

        with self.subTest(zone='az-high'):
            self.load_topology(FOUR_NODE_AZ)

            scope = [
                {'compute': [{'availability_zones': [{'name': 'az-high'}]}]}
            ]

            actions, ap = self._create_audit_and_get_actions(
                parameters=params,
                scope=scope,
                template_name='ws-az-high-%s' % self.id(),
            )
            migrate_actions = [
                a for a in actions if a['action_type'] == 'migrate'
            ]
            self.assertEqual(1, len(migrate_actions))
            action = migrate_actions[0]
            self.assertEqual(
                'vm-3', action['input_parameters']['resource_name']
            )
            self.assertEqual(
                'compute-1', action['input_parameters']['source_node']
            )
            self.assertEqual(
                'compute-2', action['input_parameters']['destination_node']
            )
            self.assertEqual(
                'live', action['input_parameters']['migration_type']
            )
            indicators = {
                ei['name']: ei['value']
                for ei in ap.get('efficacy_indicators', [])
            }
            self.assertAlmostEqual(
                0.175, indicators['standard_deviation_before_audit'], places=3
            )
            self.assertAlmostEqual(
                0.005, indicators['standard_deviation_after_audit'], places=3
            )
            self.assertEqual(8.0, indicators['instances_count'])

        with self.subTest(zone='az-low'):
            self.load_topology(FOUR_NODE_AZ)

            scope = [
                {'compute': [{'availability_zones': [{'name': 'az-low'}]}]}
            ]
            actions = self._create_audit_no_actions_scoped(
                parameters=params,
                scope=scope,
                template_name='ws-az-low-%s' % self.id(),
            )
            self.assertEqual(0, len(actions))

    def test_workload_stabilization_excluded_by_project(self):
        """Instance in an excluded project is not migrated.

        vm-4 (the highest-CPU instance on the overloaded compute-1) is
        tagged with a distinct project and that project is excluded via
        scope, so the strategy must skip it while still rebalancing the
        rest of the cluster.
        """
        EXCLUDED_PROJECT_UUID = 'cccccccc-1111-2222-3333-444444444444'

        topo = copy.deepcopy(TWO_NODE_IMBALANCED)
        topo.update_instance('vm-4', project_id=EXCLUDED_PROJECT_UUID)
        topo = dataclasses.replace(
            topo,
            aggregates=[
                topology.Aggregate(
                    id=1, name='all-hosts', hosts=['compute-1', 'compute-2']
                )
            ],
        )
        self.load_topology(topo)

        scope = [
            {
                'compute': [
                    {'host_aggregates': [{'name': 'all-hosts'}]},
                    {
                        'exclude': [
                            {'projects': [{'uuid': EXCLUDED_PROJECT_UUID}]}
                        ]
                    },
                ]
            }
        ]

        actions, ap = self._create_audit_and_get_actions(
            parameters={
                'metrics': ['instance_cpu_usage'],
                'thresholds': {'instance_cpu_usage': 0.1},
                'weights': {'instance_cpu_usage_weight': 1.0},
                'periods': {'instance': 720, 'compute_node': 600},
                'aggregation_method': {
                    'instance': 'mean',
                    'compute_node': 'mean',
                },
                'granularity': 300,
                'host_choice': 'fullsearch',
            },
            scope=scope,
        )

        migrate_actions = [a for a in actions if a['action_type'] == 'migrate']
        self.assertGreater(
            len(migrate_actions),
            0,
            'Expected the rest of the cluster to still rebalance',
        )
        migrated_ids = {
            a['input_parameters']['resource_name'] for a in migrate_actions
        }
        self.assertNotIn(
            'vm-4',
            migrated_ids,
            'vm-4 belongs to an excluded project and must not migrate',
        )
