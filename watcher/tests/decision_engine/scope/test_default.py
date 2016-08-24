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

from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.scope import default
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.scope import fake_scopes


class TestDefaultScope(base.TestCase):

    def setUp(self):
        super(TestDefaultScope, self).setUp()
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

    @mock.patch.object(nova_helper.NovaHelper, 'get_availability_zone_list')
    def test_get_scoped_model_with_zones_and_instances(self, mock_zone_list):
        cluster = self.fake_cluster.generate_scenario_1()
        audit_scope = fake_scopes.fake_scope_1
        mock_zone_list.return_value = [
            mock.Mock(zoneName='AZ{0}'.format(i),
                      hosts={'Node_{0}'.format(i): {}})
            for i in range(2)]
        model = default.DefaultScope(audit_scope,
                                     osc=mock.Mock()).get_scoped_model(cluster)
        nodes = {'Node_4': set([]), 'Node_0': set([]), 'Node_3': set([]),
                 'Node_1': set(['INSTANCE_2']), 'Node_2': set([])}
        self.assertEqual(nodes, model.get_mapping().get_mapping())

    @mock.patch.object(nova_helper.NovaHelper, 'get_availability_zone_list')
    def test_get_scoped_model_without_scope(self, mock_zone_list):
        cluster = self.fake_cluster.generate_scenario_1()
        default.DefaultScope([],
                             osc=mock.Mock()).get_scoped_model(cluster)
        assert not mock_zone_list.called

    def test__remove_instance(self):
        cluster = self.fake_cluster.generate_scenario_1()
        default.DefaultScope([],
                             osc=mock.Mock())._remove_instance(cluster,
                                                               'INSTANCE_2',
                                                               'Node_1')
        expected_map = {'Node_4': set(['INSTANCE_7']), 'Node_1': set([]),
                        'Node_0': set(['INSTANCE_0', 'INSTANCE_1']),
                        'Node_3': set(['INSTANCE_6']),
                        'Node_2': set(['INSTANCE_4', 'INSTANCE_5',
                                       'INSTANCE_3'])}
        self.assertEqual(expected_map, cluster.get_mapping().get_mapping())

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_detail')
    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test__collect_aggregates(self, mock_aggregate,
                                 mock_detailed_aggregate):
        allowed_nodes = []
        mock_aggregate.return_value = [mock.Mock(id=i) for i in range(2)]
        mock_detailed_aggregate.side_effect = [
            mock.Mock(id=i, hosts=['Node_{0}'.format(i)]) for i in range(2)]
        default.DefaultScope([{'host_aggregates': [{'id': 1}, {'id': 2}]}],
                             osc=mock.Mock())._collect_aggregates(
            [{'id': 1}, {'id': 2}], allowed_nodes)
        self.assertEqual(['Node_1'], allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_detail')
    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_aggregates_wildcard_is_used(self, mock_aggregate,
                                         mock_detailed_aggregate):
        allowed_nodes = []
        mock_aggregate.return_value = [mock.Mock(id=i) for i in range(2)]
        mock_detailed_aggregate.side_effect = [
            mock.Mock(id=i, hosts=['Node_{0}'.format(i)]) for i in range(2)]
        default.DefaultScope([{'host_aggregates': [{'id': '*'}]}],
                             osc=mock.Mock())._collect_aggregates(
            [{'id': '*'}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1'], allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_aggregates_wildcard_with_other_ids(self, mock_aggregate):
        allowed_nodes = []
        mock_aggregate.return_value = [mock.Mock(id=i) for i in range(2)]
        scope_handler = default.DefaultScope(
            [{'host_aggregates': [{'id': '*'}, {'id': 1}]}],
            osc=mock.Mock())
        self.assertRaises(exception.WildcardCharacterIsUsed,
                          scope_handler._collect_aggregates,
                          [{'id': '*'}, {'id': 1}],
                          allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_detail')
    @mock.patch.object(nova_helper.NovaHelper, 'get_aggregate_list')
    def test_aggregates_with_names_and_ids(self, mock_aggregate,
                                           mock_detailed_aggregate):
        allowed_nodes = []
        mock_aggregate.return_value = [mock.Mock(id=i,
                                                 name="HA_{0}".format(i))
                                       for i in range(2)]
        mock_collection = [mock.Mock(id=i, hosts=['Node_{0}'.format(i)])
                           for i in range(2)]
        mock_collection[0].name = 'HA_0'
        mock_collection[1].name = 'HA_1'

        mock_detailed_aggregate.side_effect = mock_collection

        default.DefaultScope([{'host_aggregates': [{'name': 'HA_1'},
                                                   {'id': 0}]}],
                             osc=mock.Mock())._collect_aggregates(
            [{'name': 'HA_1'}, {'id': 0}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1'], allowed_nodes)

    @mock.patch.object(nova_helper.NovaHelper, 'get_availability_zone_list')
    def test__collect_zones(self, mock_zone_list):
        allowed_nodes = []
        mock_zone_list.return_value = [
            mock.Mock(zoneName="AZ{0}".format(i+1),
                      hosts={'Node_{0}'.format(2*i): 1,
                             'Node_{0}'.format(2*i+1): 2})
            for i in range(2)]
        default.DefaultScope([{'availability_zones': [{'name': "AZ1"}]}],
                             osc=mock.Mock())._collect_zones(
            [{'name': "AZ1"}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1'], sorted(allowed_nodes))

    @mock.patch.object(nova_helper.NovaHelper, 'get_availability_zone_list')
    def test_zones_wildcard_is_used(self, mock_zone_list):
        allowed_nodes = []
        mock_zone_list.return_value = [
            mock.Mock(zoneName="AZ{0}".format(i+1),
                      hosts={'Node_{0}'.format(2*i): 1,
                             'Node_{0}'.format(2*i+1): 2})
            for i in range(2)]
        default.DefaultScope([{'availability_zones': [{'name': "*"}]}],
                             osc=mock.Mock())._collect_zones(
            [{'name': "*"}], allowed_nodes)
        self.assertEqual(['Node_0', 'Node_1', 'Node_2', 'Node_3'],
                         sorted(allowed_nodes))

    @mock.patch.object(nova_helper.NovaHelper, 'get_availability_zone_list')
    def test_zones_wildcard_with_other_ids(self, mock_zone_list):
        allowed_nodes = []
        mock_zone_list.return_value = [
            mock.Mock(zoneName="AZ{0}".format(i+1),
                      hosts={'Node_{0}'.format(2*i): 1,
                             'Node_{0}'.format(2*i+1): 2})
            for i in range(2)]
        scope_handler = default.DefaultScope(
            [{'availability_zones': [{'name': "*"}, {'name': 'AZ1'}]}],
            osc=mock.Mock())
        self.assertRaises(exception.WildcardCharacterIsUsed,
                          scope_handler._collect_zones,
                          [{'name': "*"}, {'name': 'AZ1'}],
                          allowed_nodes)

    def test_default_schema(self):
        test_scope = fake_scopes.default_scope
        validators.Draft4Validator(
            default.DefaultScope.DEFAULT_SCHEMA).validate(test_scope)

    def test__exclude_resources(self):
        resources_to_exclude = [{'instances': [{'uuid': 'INSTANCE_1'},
                                               {'uuid': 'INSTANCE_2'}]},
                                {'compute_nodes': [{'name': 'Node_1'},
                                                   {'name': 'Node_2'}]}
                                ]
        instances_to_exclude = []
        nodes_to_exclude = []
        default.DefaultScope([], osc=mock.Mock())._exclude_resources(
            resources_to_exclude, instances=instances_to_exclude,
            nodes=nodes_to_exclude)
        self.assertEqual(['Node_1', 'Node_2'], sorted(nodes_to_exclude))
        self.assertEqual(['INSTANCE_1', 'INSTANCE_2'],
                         sorted(instances_to_exclude))

    def test__remove_node_from_model(self):
        cluster = self.fake_cluster.generate_scenario_1()
        default.DefaultScope([], osc=mock.Mock())._remove_node_from_model(
            ['Node_1', 'Node_2'], cluster)
        expected_cluster = {'Node_0': set(['INSTANCE_0', 'INSTANCE_1']),
                            'Node_1': set([]), 'Node_2': set([]),
                            'Node_3': set(['INSTANCE_6']),
                            'Node_4': set(['INSTANCE_7'])}
        self.assertEqual(expected_cluster, cluster.get_mapping().get_mapping())

    def test__remove_instances_from_model(self):
        cluster = self.fake_cluster.generate_scenario_1()
        default.DefaultScope([], osc=mock.Mock())._remove_instances_from_model(
            ['INSTANCE_1', 'INSTANCE_2'], cluster)
        expected_cluster = {'Node_0': set(['INSTANCE_0']), 'Node_1': set([]),
                            'Node_2': set(['INSTANCE_3', 'INSTANCE_4',
                                           'INSTANCE_5']),
                            'Node_3': set(['INSTANCE_6']),
                            'Node_4': set(['INSTANCE_7'])}
        self.assertEqual(expected_cluster, cluster.get_mapping().get_mapping())
