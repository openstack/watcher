# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
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

from __future__ import unicode_literals

import functools

from oslo_log import log
from tempest import config
from tempest.lib.common.utils import test_utils

from watcher_tempest_plugin.tests.scenario import base

CONF = config.CONF
LOG = log.getLogger(__name__)


class TestExecuteWorkloadBalancingStrategy(base.BaseInfraOptimScenarioTest):
    """Tests for action plans"""

    GOAL = "workload_balancing"

    @classmethod
    def skip_checks(cls):
        super(TestExecuteWorkloadBalancingStrategy, cls).skip_checks()

    @classmethod
    def resource_setup(cls):
        super(TestExecuteWorkloadBalancingStrategy, cls).resource_setup()
        if CONF.compute.min_compute_nodes < 2:
            raise cls.skipException(
                "Less than 2 compute nodes, skipping multinode tests.")
        if not CONF.compute_feature_enabled.live_migration:
            raise cls.skipException("Live migration is not enabled")

        cls.initial_compute_nodes_setup = cls.get_compute_nodes_setup()
        enabled_compute_nodes = [cn for cn in cls.initial_compute_nodes_setup
                                 if cn.get('status') == 'enabled']

        cls.wait_for_compute_node_setup()

        if len(enabled_compute_nodes) < 2:
            raise cls.skipException(
                "Less than 2 compute nodes are enabled, "
                "skipping multinode tests.")

    @classmethod
    def get_hypervisors_setup(cls):
        hypervisors_client = cls.mgr.hypervisor_client
        hypervisors = hypervisors_client.list_hypervisors(
            detail=True)['hypervisors']
        return hypervisors

    @classmethod
    def get_compute_nodes_setup(cls):
        services_client = cls.mgr.services_client
        available_services = services_client.list_services()['services']

        return [srv for srv in available_services
                if srv.get('binary') == 'nova-compute']

    def _migrate_server_to(self, server_id, dest_host, volume_backed=False):
        kwargs = dict()
        kwargs['disk_over_commit'] = False
        block_migration = (CONF.compute_feature_enabled.
                           block_migration_for_live_migration and
                           not volume_backed)
        body = self.mgr.servers_client.live_migrate_server(
            server_id, host=dest_host, block_migration=block_migration,
            **kwargs)
        return body

    @classmethod
    def wait_for_compute_node_setup(cls):

        def _are_compute_nodes_setup():
            try:
                hypervisors = cls.get_hypervisors_setup()
                available_hypervisors = set(
                    hyp['hypervisor_hostname'] for hyp in hypervisors
                    if hyp['state'] == 'up')
                available_services = set(
                    service['host']
                    for service in cls.get_compute_nodes_setup()
                    if service['state'] == 'up')
                return (
                    len(available_hypervisors) == len(available_services) and
                    len(hypervisors) >= 2)
            except Exception as exc:
                LOG.exception(exc)
                return False

        assert test_utils.call_until_true(
            func=_are_compute_nodes_setup,
            duration=600,
            sleep_for=2
        )

    @classmethod
    def rollback_compute_nodes_status(cls):
        current_compute_nodes_setup = cls.get_compute_nodes_setup()
        for cn_setup in current_compute_nodes_setup:
            cn_hostname = cn_setup.get('host')
            matching_cns = [
                cns for cns in cls.initial_compute_nodes_setup
                if cns.get('host') == cn_hostname
            ]
            initial_cn_setup = matching_cns[0]  # Should return a single result
            if cn_setup.get('status') != initial_cn_setup.get('status'):
                if initial_cn_setup.get('status') == 'enabled':
                    rollback_func = cls.mgr.services_client.enable_service
                else:
                    rollback_func = cls.mgr.services_client.disable_service
                rollback_func(binary='nova-compute', host=cn_hostname)

    def _create_one_instance_per_host(self):
        """Create 1 instance per compute node

        This goes up to the min_compute_nodes threshold so that things don't
        get crazy if you have 1000 compute nodes but set min to 3.
        """
        host_client = self.mgr.hosts_client
        all_hosts = host_client.list_hosts()['hosts']
        compute_nodes = [x for x in all_hosts if x['service'] == 'compute']

        created_instances = []
        for _ in compute_nodes[:CONF.compute.min_compute_nodes]:
            # by getting to active state here, this means this has
            # landed on the host in question.
            created_instances.append(
                self.create_server(image_id=CONF.compute.image_ref,
                                   wait_until='ACTIVE', clients=self.mgr))
        return created_instances

    def _pack_all_created_instances_on_one_host(self, instances):
        hypervisors = [
            hyp['hypervisor_hostname'] for hyp in self.get_hypervisors_setup()
            if hyp['state'] == 'up']
        node = hypervisors[0]
        for instance in instances:
            if instance.get('OS-EXT-SRV-ATTR:hypervisor_hostname') != node:
                self._migrate_server_to(instance['id'], node)

    def test_execute_workload_stabilization(self):
        """Execute an action plan using the workload_stabilization strategy"""
        self.addCleanup(self.rollback_compute_nodes_status)
        instances = self._create_one_instance_per_host()
        self._pack_all_created_instances_on_one_host(instances)

        audit_parameters = {
            "metrics": ["cpu_util"],
            "thresholds": {"cpu_util": 0.2},
            "weights": {"cpu_util_weight": 1.0},
            "instance_metrics": {"cpu_util": "compute.node.cpu.percent"}}

        _, goal = self.client.show_goal(self.GOAL)
        _, strategy = self.client.show_strategy("workload_stabilization")
        _, audit_template = self.create_audit_template(
            goal['uuid'], strategy=strategy['uuid'])
        _, audit = self.create_audit(
            audit_template['uuid'], parameters=audit_parameters)

        try:
            self.assertTrue(test_utils.call_until_true(
                func=functools.partial(
                    self.has_audit_finished, audit['uuid']),
                duration=600,
                sleep_for=2
            ))
        except ValueError:
            self.fail("The audit has failed!")

        _, finished_audit = self.client.show_audit(audit['uuid'])
        if finished_audit.get('state') in ('FAILED', 'CANCELLED'):
            self.fail("The audit ended in unexpected state: %s!" %
                      finished_audit.get('state'))

        _, action_plans = self.client.list_action_plans(
            audit_uuid=audit['uuid'])
        action_plan = action_plans['action_plans'][0]

        _, action_plan = self.client.show_action_plan(action_plan['uuid'])
        _, action_list = self.client.list_actions(
            action_plan_uuid=action_plan["uuid"])
