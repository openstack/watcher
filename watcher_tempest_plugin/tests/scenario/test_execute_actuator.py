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

import collections
import functools

from tempest import config
from tempest.lib.common.utils import test_utils

from watcher_tempest_plugin.tests.scenario import base

CONF = config.CONF


class TestExecuteActionsViaActuator(base.BaseInfraOptimScenarioTest):

    scenarios = [
        ("nop", {"actions": [
            {"action_type": "nop",
             "input_parameters": {
                 "message": "hello World"}}]}),
        ("sleep", {"actions": [
            {"action_type": "sleep",
             "input_parameters": {
                 "duration": 1.0}}]}),
        ("change_nova_service_state", {"actions": [
            {"action_type": "change_nova_service_state",
             "input_parameters": {
                 "state": "enabled"},
             "filling_function":
                 "_prerequisite_param_for_"
                 "change_nova_service_state_action"}]}),
        ("resize", {"actions": [
            {"action_type": "resize",
             "filling_function": "_prerequisite_param_for_resize_action"}]}),
        ("migrate", {"actions": [
            {"action_type": "migrate",
             "input_parameters": {
                 "migration_type": "live"},
             "filling_function": "_prerequisite_param_for_migrate_action"},
            {"action_type": "migrate",
             "filling_function": "_prerequisite_param_for_migrate_action"}]})
    ]

    @classmethod
    def resource_setup(cls):
        super(TestExecuteActionsViaActuator, cls).resource_setup()
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
    def get_compute_nodes_setup(cls):
        services_client = cls.mgr.services_client
        available_services = services_client.list_services()['services']

        return [srv for srv in available_services
                if srv.get('binary') == 'nova-compute']

    @classmethod
    def wait_for_compute_node_setup(cls):

        def _are_compute_nodes_setup():
            try:
                hypervisors_client = cls.mgr.hypervisor_client
                hypervisors = hypervisors_client.list_hypervisors(
                    detail=True)['hypervisors']
                available_hypervisors = set(
                    hyp['hypervisor_hostname'] for hyp in hypervisors)
                available_services = set(
                    service['host']
                    for service in cls.get_compute_nodes_setup())

                return (
                    available_hypervisors == available_services and
                    len(hypervisors) >= 2)
            except Exception:
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

        created_servers = []
        for _ in compute_nodes[:CONF.compute.min_compute_nodes]:
            # by getting to active state here, this means this has
            # landed on the host in question.
            created_servers.append(
                self.create_server(image_id=CONF.compute.image_ref,
                                   wait_until='ACTIVE',
                                   clients=self.mgr))

        return created_servers

    def _get_flavors(self):
        return self.mgr.flavors_client.list_flavors()['flavors']

    def _prerequisite_param_for_migrate_action(self):
        created_instances = self._create_one_instance_per_host()
        instance = created_instances[0]
        source_node = created_instances[0]["OS-EXT-SRV-ATTR:host"]
        destination_node = created_instances[-1]["OS-EXT-SRV-ATTR:host"]

        parameters = {
            "resource_id": instance['id'],
            "migration_type": "live",
            "source_node": source_node,
            "destination_node": destination_node
        }

        return parameters

    def _prerequisite_param_for_resize_action(self):
        created_instances = self._create_one_instance_per_host()
        instance = created_instances[0]
        current_flavor_id = instance['flavor']['id']

        flavors = self._get_flavors()
        new_flavors = [f for f in flavors if f['id'] != current_flavor_id]
        new_flavor = new_flavors[0]

        parameters = {
            "resource_id": instance['id'],
            "flavor": new_flavor['name']
        }

        return parameters

    def _prerequisite_param_for_change_nova_service_state_action(self):
        enabled_compute_nodes = [cn for cn in
                                 self.initial_compute_nodes_setup
                                 if cn.get('status') == 'enabled']
        enabled_compute_node = enabled_compute_nodes[0]

        parameters = {
            "resource_id": enabled_compute_node['host'],
            "state": "enabled"
        }

        return parameters

    def _fill_actions(self, actions):
        for action in actions:
            filling_function_name = action.pop('filling_function', None)

            if filling_function_name is not None:
                filling_function = getattr(self, filling_function_name, None)

                if filling_function is not None:
                    parameters = filling_function()

                    resource_id = parameters.pop('resource_id', None)

                    if resource_id is not None:
                        action['resource_id'] = resource_id

                    input_parameters = action.get('input_parameters', None)

                    if input_parameters is not None:
                        parameters.update(input_parameters)
                        input_parameters.update(parameters)
                    else:
                        action['input_parameters'] = parameters

    def _execute_actions(self, actions):
        self.wait_for_all_action_plans_to_finish()

        _, goal = self.client.show_goal("unclassified")
        _, strategy = self.client.show_strategy("actuator")
        _, audit_template = self.create_audit_template(
            goal['uuid'], strategy=strategy['uuid'])
        _, audit = self.create_audit(
            audit_template['uuid'], parameters={"actions": actions})

        self.assertTrue(test_utils.call_until_true(
            func=functools.partial(self.has_audit_succeeded, audit['uuid']),
            duration=30,
            sleep_for=.5
        ))
        _, action_plans = self.client.list_action_plans(
            audit_uuid=audit['uuid'])
        action_plan = action_plans['action_plans'][0]

        _, action_plan = self.client.show_action_plan(action_plan['uuid'])

        # Execute the action plan
        _, updated_ap = self.client.start_action_plan(action_plan['uuid'])

        self.assertTrue(test_utils.call_until_true(
            func=functools.partial(
                self.has_action_plan_finished, action_plan['uuid']),
            duration=300,
            sleep_for=1
        ))
        _, finished_ap = self.client.show_action_plan(action_plan['uuid'])
        _, action_list = self.client.list_actions(
            action_plan_uuid=finished_ap["uuid"])

        self.assertIn(updated_ap['state'], ('PENDING', 'ONGOING'))
        self.assertIn(finished_ap['state'], ('SUCCEEDED', 'SUPERSEDED'))

        expected_action_counter = collections.Counter(
            act['action_type'] for act in actions)
        action_counter = collections.Counter(
            act['action_type'] for act in action_list['actions'])

        self.assertEqual(expected_action_counter, action_counter)

    def test_execute_nop(self):
        self.addCleanup(self.rollback_compute_nodes_status)

        actions = [{
            "action_type": "nop",
            "input_parameters": {"message": "hello World"}}]
        self._execute_actions(actions)

    def test_execute_sleep(self):
        self.addCleanup(self.rollback_compute_nodes_status)

        actions = [
            {"action_type": "sleep",
             "input_parameters": {"duration": 1.0}}
        ]
        self._execute_actions(actions)

    def test_execute_change_nova_service_state(self):
        self.addCleanup(self.rollback_compute_nodes_status)

        enabled_compute_nodes = [
            cn for cn in self.initial_compute_nodes_setup
            if cn.get('status') == 'enabled']

        enabled_compute_node = enabled_compute_nodes[0]
        actions = [
            {"action_type": "change_nova_service_state",
             "resource_id": enabled_compute_node['host'],
             "input_parameters": {"state": "enabled"}}
        ]
        self._execute_actions(actions)

    def test_execute_resize(self):
        self.addCleanup(self.rollback_compute_nodes_status)

        created_instances = self._create_one_instance_per_host()
        instance = created_instances[0]
        current_flavor_id = instance['flavor']['id']

        flavors = self._get_flavors()
        new_flavors = [f for f in flavors if f['id'] != current_flavor_id]
        new_flavor = new_flavors[0]

        actions = [
            {"action_type": "resize",
             "resource_id": instance['id'],
             "input_parameters": {"flavor": new_flavor['name']}}
        ]
        self._execute_actions(actions)

    def test_execute_migrate(self):
        self.addCleanup(self.rollback_compute_nodes_status)

        created_instances = self._create_one_instance_per_host()
        instance = created_instances[0]
        source_node = created_instances[0]["OS-EXT-SRV-ATTR:host"]
        destination_node = created_instances[-1]["OS-EXT-SRV-ATTR:host"]
        actions = [
            {"action_type": "migrate",
             "resource_id": instance['id'],
             "input_parameters": {
                 "migration_type": "live",
                 "source_node": source_node,
                 "destination_node": destination_node}}
        ]
        self._execute_actions(actions)

    def test_execute_scenarios(self):
        self.addCleanup(self.rollback_compute_nodes_status)

        for _, scenario in self.scenarios:
            actions = scenario['actions']
            self._fill_actions(actions)
            self._execute_actions(actions)
