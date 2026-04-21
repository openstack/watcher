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

from http import HTTPStatus
from unittest import mock

import ddt

from oslo_serialization import jsonutils
from oslo_versionedobjects import fields as ovo_fields

from watcher.api.controllers.v1 import data_model as dm_ctrl
from watcher.api.controllers.v1 import versions
from watcher.decision_engine import rpcapi as deapi
from watcher.objects import fields as wfields
from watcher.tests.unit.api import base as api_base
from watcher.tests.unit.decision_engine.model import faker_cluster_state


class TestListDataModel(api_base.FunctionalTest):
    def setUp(self):
        super().setUp()
        p_dcapi = mock.patch.object(deapi, 'DecisionEngineAPI')
        self.mock_dcapi = p_dcapi.start()
        # server_uuid is in FROZEN_SERVER_FIELDS, so it survives the filter.
        self.fake_response = {'context': [{'server_uuid': 'fake_uuid'}]}
        self.mock_dcapi().get_data_model_info.return_value = self.fake_response
        self.addCleanup(p_dcapi.stop)

    def test_get_all(self):
        response = self.get_json(
            '/data_model/?data_model_type=compute',
            headers={'OpenStack-API-Version': 'infra-optim 1.3'},
        )
        self.assertEqual(self.fake_response, response)

    def test_get_all_not_acceptable(self):
        response = self.get_json(
            '/data_model/?data_model_type=compute',
            headers={'OpenStack-API-Version': 'infra-optim 1.2'},
            expect_errors=True,
        )
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
        'node_uuid',
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
        'server_uuid',
    ]

    SERVER_FIELDS_1_6 = [
        'server_pinned_az',
        'server_flavor_extra_specs',
    ] + SERVER_FIELDS_1_3

    # Map of API version to expected server fields
    SERVER_FIELDS_MAP = {
        '1.3': SERVER_FIELDS_1_3,
        '1.6': SERVER_FIELDS_1_6,
        'latest': SERVER_FIELDS_1_6,
    }

    def setUp(self):
        super().setUp()
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
            headers={'OpenStack-API-Version': infra_max_version},
        )

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
            headers={'OpenStack-API-Version': infra_max_version},
        )

        server_info = response.get("context")[0]
        expected_keys = (
            self.NODE_FIELDS_MAP[version] + self.SERVER_FIELDS_MAP[version]
        )

        self.assertEqual(len(response.get("context")), 2)
        self.assertEqual(set(expected_keys), set(server_info.keys()))


class TestDataModelPolicyEnforcement(api_base.FunctionalTest):
    def setUp(self):
        super().setUp()
        p_dcapi = mock.patch.object(deapi, 'DecisionEngineAPI')
        self.mock_dcapi = p_dcapi.start()
        self.addCleanup(p_dcapi.stop)

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules(
            {
                "admin_api": "(role:admin or role:administrator)",
                "default": "rule:admin_api",
                rule: "rule:default",
            }
        )
        response = func(*arg, **kwarg)
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            f"Policy doesn't allow {rule} to be performed.",
            jsonutils.loads(response.json['error_message'])['faultstring'],
        )

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "data_model:get_all",
            self.get_json,
            "/data_model/?data_model_type=compute",
            headers={'OpenStack-API-Version': 'infra-optim 1.3'},
            expect_errors=True,
        )


class TestDataModelEnforcementWithAdminContext(
    TestListDataModel, api_base.AdminRoleTest
):
    def setUp(self):
        super().setUp()
        self.policy.set_rules(
            {
                "admin_api": "(role:admin or role:administrator)",
                "default": "rule:admin_api",
                "data_model:get_all": "rule:default",
            }
        )


class TestFilterDataModelFields(api_base.FunctionalTest):
    """Verify unknown internal fields are stripped from the API response."""

    def setUp(self):
        super().setUp()
        p_dcapi = mock.patch.object(deapi, 'DecisionEngineAPI')
        self.mock_dcapi = p_dcapi.start()
        self.addCleanup(p_dcapi.stop)

    def _get_data_model(self, fake_response, version='1.6'):
        self.mock_dcapi().get_data_model_info.return_value = fake_response
        return self.get_json(
            '/data_model/?data_model_type=compute',
            headers={'OpenStack-API-Version': 'infra-optim %s' % version},
        )

    def test_unknown_node_field_is_stripped(self):
        fake_response = {
            'context': [
                {
                    'node_uuid': 'fake-node-uuid',
                    'node_hostname': 'compute-0',
                    'node_future_internal_field': 'should-be-stripped',
                }
            ]
        }
        response = self._get_data_model(fake_response)
        entry = response['context'][0]
        self.assertNotIn('node_future_internal_field', entry)
        self.assertIn('node_uuid', entry)
        self.assertIn('node_hostname', entry)

    def test_unknown_server_field_is_stripped(self):
        fake_response = {
            'context': [
                {
                    'node_uuid': 'fake-node-uuid',
                    'server_uuid': 'fake-server-uuid',
                    'server_future_internal_field': 'should-be-stripped',
                }
            ]
        }
        response = self._get_data_model(fake_response)
        entry = response['context'][0]
        self.assertNotIn('server_future_internal_field', entry)
        self.assertIn('node_uuid', entry)
        self.assertIn('server_uuid', entry)

    def test_unknown_fields_stripped_alongside_version_hiding(self):
        """Unknown fields are removed even when version-based hiding runs."""
        fake_response = {
            'context': [
                {
                    'node_uuid': 'fake-node-uuid',
                    'server_uuid': 'fake-server-uuid',
                    'server_pinned_az': 'nova',
                    'server_flavor_extra_specs': {},
                    'server_future_internal_field': 'should-be-stripped',
                }
            ]
        }
        # v1.3 hides pinned_az and flavor_extra_specs; the unknown field must
        # also be absent regardless of the version filtering order.
        response = self._get_data_model(fake_response, version='1.3')
        entry = response['context'][0]
        self.assertNotIn('server_future_internal_field', entry)
        self.assertNotIn('server_pinned_az', entry)
        self.assertNotIn('server_flavor_extra_specs', entry)
        self.assertIn('server_uuid', entry)
        self.assertIn('node_uuid', entry)

    def test_all_frozen_node_fields_are_preserved(self):
        fake_response = {
            'context': [{f: 'value' for f in dm_ctrl.FROZEN_NODE_FIELDS}]
        }
        response = self._get_data_model(fake_response)
        entry = response['context'][0]
        self.assertEqual(dm_ctrl.FROZEN_NODE_FIELDS, set(entry.keys()))

    def test_all_frozen_server_fields_preserved_in_v16(self):
        row = {f: 'value' for f in dm_ctrl.FROZEN_NODE_FIELDS}
        row.update({f: 'value' for f in dm_ctrl.FROZEN_SERVER_FIELDS})
        fake_response = {'context': [row]}
        response = self._get_data_model(fake_response, version='1.6')
        entry = response['context'][0]
        expected = dm_ctrl.FROZEN_NODE_FIELDS | dm_ctrl.FROZEN_SERVER_FIELDS
        self.assertEqual(expected, set(entry.keys()))

    @staticmethod
    def _fill_missing_fields(obj):
        """Set a dummy value on every field that has not been assigned yet.

        oslo.versionedobjects raises NotImplementedError when a field has no
        value and no default.  Filling those gaps ensures to_list() emits
        every field key, so the filter is exercised for optional fields that
        the faker leaves unset.
        """
        _dummy = [
            (wfields.UUIDField, '00000000-0000-0000-0000-000000000000'),
            (ovo_fields.BooleanField, False),
            (ovo_fields.NonNegativeFloatField, 1.0),
            (ovo_fields.NonNegativeIntegerField, 0),
            (wfields.JsonField, {}),
        ]
        for name, field in obj.fields.items():
            try:
                obj[name]
            except NotImplementedError:
                for cls, val in _dummy:
                    if isinstance(field, cls):
                        obj[name] = val
                        break
                else:
                    obj[name] = None if field.nullable else 'fake'

    def test_all_model_fields_filtered_to_frozen_set(self):
        """All fields on real model objects reach the filter.

        The faker may leave optional fields (no default) unset, causing
        to_list() to silently omit them.  _fill_missing_fields() patches
        those gaps so to_list() emits every field key and the filter is
        exercised for all of them, including future optional additions.
        """
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_11_with_2_nodes_2_instances()

        for node in model.get_all_compute_nodes().values():
            self._fill_missing_fields(node)
        for instance in model.get_all_instances().values():
            self._fill_missing_fields(instance)

        get_model_resp = {'context': model.to_list()}
        response = self._get_data_model(get_model_resp, version='1.6')
        entry = response['context'][0]
        expected = dm_ctrl.FROZEN_NODE_FIELDS | dm_ctrl.FROZEN_SERVER_FIELDS
        self.assertEqual(expected, set(entry.keys()))
