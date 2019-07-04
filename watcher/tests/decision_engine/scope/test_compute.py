# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica
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
#

from jsonschema import validators
import mock

from watcher.api.controllers.v1 import audit_template
from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.scope import compute
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.scope import fake_scopes


class TestComputeScope(base.TestCase):

    def setUp(self):
        super(TestComputeScope, self).setUp()
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

    @mock.patch.object(nova_helper.NovaHelper, 'get_service_list')
    def test_get_scoped_model_with_zones_and_instances(self, mock_zone_list):
        cluster = self.fake_cluster.generate_scenario_1()
        audit_scope = fake_scopes.fake_scope_1
        mock_zone_list.return_value = [
            mock.Mock(zone='AZ{0}'.format(i),
                      host={'hostname_{0}'.format(i): {}})
            for i in range(4)]
        model = compute.ComputeScope(audit_scope, mock.Mock(),
                                     osc=mock.Mock()).get_scoped_model(cluster)

        # NOTE(adisky):INSTANCE_6 is not excluded from model it will be tagged
        # as 'exclude' TRUE, blueprint compute-cdm-include-all-instances
        expected_edges = [('INSTANCE_2', 'Node_1'), (u'INSTANCE_6', u'Node_3')]
        self.assertEqual(sorted(expected_edges), sorted(model.edges()))

    @mock.patch.object(nova_helper.NovaHelper, 'get_service_list')
    def test_get_scoped_model_without_scope(self, mock_zone_list):
        model = self.fake_cluster.generate_scenario_1()
        compute.ComputeScope([], mock.Mock(),
                             osc=mock.Mock()).get_scoped_model(model)
        assert not mock_zone_list.called

    def test_remove_instance(self):
        model = self.fake_cluster.generate_scenario_1()
        compute.ComputeScope([], mock.Mock(), osc=mock.Mock()).remove_instance(
            model, model.get_instance_by_uuid('INSTANCE_2'), 'Node_1')
        expected_edges = [
            ('INSTANCE_0', 'Node_0'),
            ('INSTANCE_1', 'Node_0'),
            ('INSTANCE_3', 'Node_2'),
            ('INSTANCE_4', 'Node_2'),
            ('INSTANCE_5', 'Node_2'),
            ('INSTANCE_6', 'Node_3'),
            ('INSTANCE_7', 'Node_4'),
        ]
        self.assertEqual(sorted(expected_edges), sorted(model.edges()))

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_collect_aggregates(self, mock_aggregate):
        allowed_nodes = []
        mock_aggregate.return_value = [
            mock.Mock(id=i, hosts=['Node_{0}'.format(i)]) for i in range(2)]
        compute.ComputeScope([{'host_aggregates': [{'id': 1}, {'id': 2}]}],
                             mock.Mock(), osc=mock.Mock())._collect_aggregates(
            [{'id': 1}, {'id': 2}], allowed_nodes)
        self.assertEqual(['Node_1'], allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_aggregates_wildcard_is_used(self, mock_aggregate):
        allowed_nodes = []
        mock_aggregate.return_value = [
            mock.Mock(id=i, hosts=['Node_{0}'.format(i)]) for i in range(2)]
        compute.ComputeScope([{'host_aggregates': [{'id': '*'}]}],
                             mock.Mock(), osc=mock.Mock())._collect_aggregates(
            [{'id': '*'}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1'], allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_aggregates_wildcard_with_other_ids(self, mock_aggregate):
        allowed_nodes = []
        mock_aggregate.return_value = [mock.Mock(id=i) for i in range(2)]
        scope_handler = compute.ComputeScope(
            [{'host_aggregates': [{'id': '*'}, {'id': 1}]}],
            mock.Mock(), osc=mock.Mock())
        self.assertRaises(exception.WildcardCharacterIsUsed,
                          scope_handler._collect_aggregates,
                          [{'id': '*'}, {'id': 1}],
                          allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_aggregates_with_names_and_ids(self, mock_aggregate):
        allowed_nodes = []
        mock_collection = [mock.Mock(id=i, hosts=['Node_{0}'.format(i)])
                           for i in range(2)]
        mock_collection[0].name = 'HA_0'
        mock_collection[1].name = 'HA_1'

        mock_aggregate.return_value = mock_collection

        compute.ComputeScope([{'host_aggregates': [{'name': 'HA_1'},
                                                   {'id': 0}]}],
                             mock.Mock(), osc=mock.Mock())._collect_aggregates(
            [{'name': 'HA_1'}, {'id': 0}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1'], allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_service_list')
    def test_collect_zones(self, mock_zone_list):
        allowed_nodes = []
        mock_zone_list.return_value = [
            mock.Mock(zone="AZ{0}".format(i + 1),
                      host={'Node_{0}'.format(2 * i): 1,
                            'Node_{0}'.format(2 * i + 1): 2})
            for i in range(2)]
        compute.ComputeScope([{'availability_zones': [{'name': "AZ1"}]}],
                             mock.Mock(), osc=mock.Mock())._collect_zones(
            [{'name': "AZ1"}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1'], sorted(allowed_nodes))

    @mock.patch.object(nova_helper.NovaHelper, 'get_service_list')
    def test_zones_wildcard_is_used(self, mock_zone_list):
        allowed_nodes = []
        mock_zone_list.return_value = [
            mock.Mock(zone="AZ{0}".format(i + 1),
                      host={'Node_{0}'.format(2 * i): 1,
                            'Node_{0}'.format(2 * i + 1): 2})
            for i in range(2)]
        compute.ComputeScope([{'availability_zones': [{'name': "*"}]}],
                             mock.Mock(), osc=mock.Mock())._collect_zones(
            [{'name': "*"}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1', 'Node_2', 'Node_3'],
                         sorted(allowed_nodes))

    @mock.patch.object(nova_helper.NovaHelper, 'get_service_list')
    def test_zones_wildcard_with_other_ids(self, mock_zone_list):
        allowed_nodes = []
        mock_zone_list.return_value = [
            mock.Mock(zone="AZ{0}".format(i + 1),
                      host={'Node_{0}'.format(2 * i): 1,
                            'Node_{0}'.format(2 * i + 1): 2})
            for i in range(2)]
        scope_handler = compute.ComputeScope(
            [{'availability_zones': [{'name': "*"}, {'name': 'AZ1'}]}],
            mock.Mock(), osc=mock.Mock())
        self.assertRaises(exception.WildcardCharacterIsUsed,
                          scope_handler._collect_zones,
                          [{'name': "*"}, {'name': 'AZ1'}],
                          allowed_nodes)

    def test_compute_schema(self):
        test_scope = fake_scopes.compute_scope
        validators.Draft4Validator(
            audit_template.AuditTemplatePostType._build_schema()
            ).validate(test_scope)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_exclude_resource(self, mock_aggregate):
        mock_collection = [mock.Mock(id=i, hosts=['Node_{0}'.format(i)])
                           for i in range(2)]
        mock_collection[0].name = 'HA_0'
        mock_collection[1].name = 'HA_1'
        mock_aggregate.return_value = mock_collection

        resources_to_exclude = [{'host_aggregates': [{'name': 'HA_1'},
                                                     {'id': 0}]},
                                {'instances': [{'uuid': 'INSTANCE_1'},
                                               {'uuid': 'INSTANCE_2'}]},
                                {'compute_nodes': [{'name': 'Node_2'},
                                                   {'name': 'Node_3'}]},
                                {'instance_metadata': [{'optimize': True},
                                                       {'optimize1': False}]},
                                {'projects': [{'uuid': 'PROJECT_1'},
                                              {'uuid': 'PROJECT_2'}]}]
        instances_to_exclude = []
        nodes_to_exclude = []
        instance_metadata = []
        projects_to_exclude = []
        compute.ComputeScope([], mock.Mock(),
                             osc=mock.Mock()).exclude_resources(
            resources_to_exclude, instances=instances_to_exclude,
            nodes=nodes_to_exclude, instance_metadata=instance_metadata,
            projects=projects_to_exclude)

        self.assertEqual(['Node_0', 'Node_1', 'Node_2', 'Node_3'],
                         sorted(nodes_to_exclude))
        self.assertEqual(['INSTANCE_1', 'INSTANCE_2'],
                         sorted(instances_to_exclude))
        self.assertEqual([{'optimize': True}, {'optimize1': False}],
                         instance_metadata)
        self.assertEqual(['PROJECT_1', 'PROJECT_2'],
                         sorted(projects_to_exclude))

    def test_exclude_instances_with_given_metadata(self):
        cluster = self.fake_cluster.generate_scenario_1()
        instance_metadata = [{'optimize': True}]
        instances_to_remove = set()
        compute.ComputeScope(
            [], mock.Mock(),
            osc=mock.Mock()).exclude_instances_with_given_metadata(
                instance_metadata, cluster, instances_to_remove)
        self.assertEqual(sorted(['INSTANCE_' + str(i) for i in range(35)]),
                         sorted(instances_to_remove))

        instance_metadata = [{'optimize': False}]
        instances_to_remove = set()
        compute.ComputeScope(
            [], mock.Mock(),
            osc=mock.Mock()).exclude_instances_with_given_metadata(
                instance_metadata, cluster, instances_to_remove)
        self.assertEqual(set(), instances_to_remove)

    def test_exclude_instances_with_given_project(self):
        cluster = self.fake_cluster.generate_scenario_1()
        instances_to_exclude = set()
        projects_to_exclude = ['26F03131-32CB-4697-9D61-9123F87A8147',
                               '109F7909-0607-4712-B32C-5CC6D49D2F15']
        compute.ComputeScope(
            [], mock.Mock(),
            osc=mock.Mock()).exclude_instances_with_given_project(
                projects_to_exclude, cluster, instances_to_exclude)
        self.assertEqual(['INSTANCE_1', 'INSTANCE_2'],
                         sorted(instances_to_exclude))

    def test_remove_nodes_from_model(self):
        model = self.fake_cluster.generate_scenario_1()
        compute.ComputeScope([], mock.Mock(),
                             osc=mock.Mock()).remove_nodes_from_model(
            ['hostname_1', 'hostname_2'], model)
        expected_edges = [
            ('INSTANCE_0', 'Node_0'),
            ('INSTANCE_1', 'Node_0'),
            ('INSTANCE_6', 'Node_3'),
            ('INSTANCE_7', 'Node_4')]
        self.assertEqual(sorted(expected_edges), sorted(model.edges()))

    def test_update_exclude_instances_in_model(self):
        model = self.fake_cluster.generate_scenario_1()
        compute.ComputeScope([], mock.Mock(),
                             osc=mock.Mock()).update_exclude_instance_in_model(
            ['INSTANCE_1', 'INSTANCE_2'], model)
        expected_edges = [
            ('INSTANCE_0', 'Node_0'),
            ('INSTANCE_1', 'Node_0'),
            ('INSTANCE_2', 'Node_1'),
            ('INSTANCE_3', 'Node_2'),
            ('INSTANCE_4', 'Node_2'),
            ('INSTANCE_5', 'Node_2'),
            ('INSTANCE_6', 'Node_3'),
            ('INSTANCE_7', 'Node_4')]
        self.assertEqual(sorted(expected_edges), sorted(model.edges()))
        self.assertFalse(
            model.get_instance_by_uuid('INSTANCE_0').watcher_exclude)
        self.assertTrue(
            model.get_instance_by_uuid('INSTANCE_1').watcher_exclude)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_detail')
    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_get_scoped_model_with_hostaggregate_null(
            self, mock_list, mock_detail):
        cluster = self.fake_cluster.generate_scenario_1()
        audit_scope = fake_scopes.fake_scope_3
        mock_list.return_value = [mock.Mock(id=i,
                                            name="HA_{0}".format(i))
                                  for i in range(2)]
        model = compute.ComputeScope(audit_scope, mock.Mock(),
                                     osc=mock.Mock()).get_scoped_model(cluster)
        self.assertEqual(0, len(model.edges()))

    @mock.patch.object(nova_helper.NovaHelper, 'get_service_list')
    def test_get_scoped_model_with_multi_scopes(self, mock_zone_list):
        cluster = self.fake_cluster.generate_scenario_1()
        # includes compute and storage scope
        audit_scope = []
        audit_scope.extend(fake_scopes.fake_scope_1)
        audit_scope.extend(fake_scopes.fake_scope_2)
        mock_zone_list.return_value = [
            mock.Mock(zone='AZ{0}'.format(i),
                      host={'hostname_{0}'.format(i): {}})
            for i in range(4)]
        model = compute.ComputeScope(audit_scope, mock.Mock(),
                                     osc=mock.Mock()).get_scoped_model(cluster)

        # NOTE(adisky):INSTANCE_6 is not excluded from model it will be tagged
        # as 'exclude' TRUE, blueprint compute-cdm-include-all-instances
        expected_edges = [('INSTANCE_2', 'Node_1'), (u'INSTANCE_6', u'Node_3')]
        self.assertEqual(sorted(expected_edges), sorted(model.edges()))
