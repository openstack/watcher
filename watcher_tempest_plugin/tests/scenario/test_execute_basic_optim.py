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

from tempest import config
from tempest import test

from watcher_tempest_plugin.tests.scenario import base

CONF = config.CONF


class TestExecuteBasicStrategy(base.BaseInfraOptimScenarioTest):
    """Tests for action plans"""

    BASIC_GOAL = "server_consolidation"

    @classmethod
    def skip_checks(cls):
        super(TestExecuteBasicStrategy, cls).skip_checks()

    @classmethod
    def resource_setup(cls):
        super(TestExecuteBasicStrategy, cls).resource_setup()
        if CONF.compute.min_compute_nodes < 2:
            raise cls.skipException(
                "Less than 2 compute nodes, skipping multinode tests.")
        if not CONF.compute_feature_enabled.live_migration:
            raise cls.skipException("Live migration is not enabled")

        cls.initial_compute_nodes_setup = cls.get_compute_nodes_setup()
        enabled_compute_nodes = [cn for cn in cls.initial_compute_nodes_setup
                                 if cn.get('status') == 'enabled']

        if len(enabled_compute_nodes) < 2:
            raise cls.skipException(
                "Less than 2 compute nodes are enabled, "
                "skipping multinode tests.")

    @classmethod
    def get_compute_nodes_setup(cls):
        services_client = cls.mgr.services_client
        available_services = services_client.list_services()['services']

        return [srv for srv in available_services
                if srv.get('binary') == 'nova-compute']

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

        for _ in compute_nodes[:CONF.compute.min_compute_nodes]:
            # by getting to active state here, this means this has
            # landed on the host in question.
            self.create_server(image_id=CONF.compute.image_ref,
                               wait_until='ACTIVE',
                               clients=self.mgr)

    def test_execute_basic_action_plan(self):
        """Execute an action plan based on the BASIC strategy

        - create an audit template with the basic strategy
        - run the audit to create an action plan
        - get the action plan
        - run the action plan
        - get results and make sure it succeeded
        """
        self.addCleanup(self.rollback_compute_nodes_status)
        self._create_one_instance_per_host()
        _, goal = self.client.show_goal(self.BASIC_GOAL)
        _, audit_template = self.create_audit_template(goal['uuid'])
        _, audit = self.create_audit(audit_template['uuid'])

        self.assertTrue(test.call_until_true(
            func=functools.partial(self.has_audit_succeeded, audit['uuid']),
            duration=600,
            sleep_for=2
        ))
        _, action_plans = self.client.list_action_plans(
            audit_uuid=audit['uuid'])
        action_plan = action_plans['action_plans'][0]

        _, action_plan = self.client.show_action_plan(action_plan['uuid'])

        # Execute the action by changing its state to PENDING
        _, updated_ap = self.client.update_action_plan(
            action_plan['uuid'],
            patch=[{'path': '/state', 'op': 'replace', 'value': 'PENDING'}]
        )

        self.assertTrue(test.call_until_true(
            func=functools.partial(
                self.has_action_plan_finished, action_plan['uuid']),
            duration=600,
            sleep_for=2
        ))
        _, finished_ap = self.client.show_action_plan(action_plan['uuid'])
        _, action_list = self.client.list_actions(
            action_plan_uuid=finished_ap["uuid"])

        self.assertIn(updated_ap['state'], ('PENDING', 'ONGOING'))
        self.assertEqual('SUCCEEDED', finished_ap['state'])

        for action in action_list['actions']:
            self.assertEqual('SUCCEEDED', action.get('state'))
