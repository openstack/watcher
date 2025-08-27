# Copyright 2019 ZTE corporation.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import ddt
from unittest import mock

from http import HTTPStatus
from oslo_serialization import jsonutils

from watcher.api.controllers.v1 import versions
from watcher.decision_engine import rpcapi as deapi
from watcher.tests.api import base as api_base
from watcher.tests.decision_engine.model import faker_cluster_state


class TestListDataModel(api_base.FunctionalTest):

    def setUp(self):
        super(TestListDataModel, self).setUp()
        p_dcapi = mock.patch.object(deapi, 'DecisionEngineAPI')
        self.mock_dcapi = p_dcapi.start()
        self.fake_response = {'context': [{'server_uuid': 'fake_uuid'}]}
        self.mock_dcapi().get_data_model_info.return_value = (
            self.fake_response)
        self.addCleanup(p_dcapi.stop)

    def test_get_all(self):
        response = self.get_json(
            '/data_model/?data_model_type=compute',
            headers={'OpenStack-API-Version': 'infra-optim 1.3'})
        self.assertEqual(self.fake_response, response)

    def test_get_all_not_acceptable(self):
        response = self.get_json(
            '/data_model/?data_model_type=compute',
            headers={'OpenStack-API-Version': 'infra-optim 1.2'},
            expect_errors=True)
        self.assertEqual(HTTPStatus.NOT_ACCEPTABLE, response.status_int)


@ddt.ddt
class TestListDataModelResponse(api_base.FunctionalTest):

    NODE_FIELDS_1_3 = [
        'node_disabled_reason',
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
        'node_uuid'
    ]

    # Map of API version to expected node fields
    NODE_FIELDS_MAP = {
        '1.3': NODE_FIELDS_1_3,
        '1.6': NODE_FIELDS_1_3,
        'latest': NODE_FIELDS_1_3,
    }

    SERVER_FIELDS_1_3 = [
        'server_watcher_exclude',
        'server_name',
        'server_state',
        'server_memory',
        'server_disk',
        'server_vcpus',
        'server_metadata',
        'server_project_id',
        'server_locked',
        'server_uuid'
    ]

    SERVER_FIELDS_1_6 = [
        'server_pinned_az',
        'server_flavor_extra_specs'
    ] + SERVER_FIELDS_1_3

    # Map of API version to expected server fields
    SERVER_FIELDS_MAP = {
        '1.3': SERVER_FIELDS_1_3,
        '1.6': SERVER_FIELDS_1_6,
        'latest': SERVER_FIELDS_1_6,
    }

    def setUp(self):
        super(TestListDataModelResponse, self).setUp()
        p_dcapi = mock.patch.object(deapi, 'DecisionEngineAPI')
        self.mock_dcapi = p_dcapi.start()
        self.addCleanup(p_dcapi.stop)

    @ddt.data("1.3", "1.6", versions.max_version_string())
    def test_model_list_compute_no_instance(self, version):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_11_with_1_node_no_instance()
        get_model_resp = {'context': model.to_list()}

        self.mock_dcapi().get_data_model_info.return_value = get_model_resp
        infra_max_version = 'infra-optim ' + version
        response = self.get_json(
            '/data_model/?data_model_type=compute',
            headers={'OpenStack-API-Version': infra_max_version})

        server_info = response.get("context")[0]
        expected_keys = self.NODE_FIELDS_MAP[version]

        self.assertEqual(len(response.get("context")), 1)
        self.assertEqual(set(expected_keys), set(server_info.keys()))

    @ddt.data("1.3", "1.6", versions.max_version_string())
    def test_model_list_compute_with_instances(self, version):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_11_with_2_nodes_2_instances()
        get_model_resp = {'context': model.to_list()}

        self.mock_dcapi().get_data_model_info.return_value = get_model_resp
        infra_max_version = 'infra-optim ' + version
        response = self.get_json(
            '/data_model/?data_model_type=compute',
            headers={'OpenStack-API-Version': infra_max_version})

        server_info = response.get("context")[0]
        expected_keys = (self.NODE_FIELDS_MAP[version] +
                         self.SERVER_FIELDS_MAP[version])

        self.assertEqual(len(response.get("context")), 2)
        self.assertEqual(set(expected_keys), set(server_info.keys()))


class TestDataModelPolicyEnforcement(api_base.FunctionalTest):

    def setUp(self):
        super(TestDataModelPolicyEnforcement, self).setUp()
        p_dcapi = mock.patch.object(deapi, 'DecisionEngineAPI')
        self.mock_dcapi = p_dcapi.start()
        self.addCleanup(p_dcapi.stop)

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            rule: "rule:default"})
        response = func(*arg, **kwarg)
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            jsonutils.loads(response.json['error_message'])['faultstring'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "data_model:get_all", self.get_json,
            "/data_model/?data_model_type=compute",
            headers={'OpenStack-API-Version': 'infra-optim 1.3'},
            expect_errors=True)


class TestDataModelEnforcementWithAdminContext(
        TestListDataModel, api_base.AdminRoleTest):

    def setUp(self):
        super(TestDataModelEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "data_model:get_all": "rule:default"})
