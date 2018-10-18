# -*- encoding: utf-8 -*-
# Copyright (c) 2018 NEC Corportion
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

import mock

from watcher.common import cinder_helper
from watcher.common import exception
from watcher.decision_engine.scope import storage
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.scope import fake_scopes


class TestStorageScope(base.TestCase):

    def setUp(self):
        super(TestStorageScope, self).setUp()
        self.fake_cluster = faker_cluster_state.FakerStorageModelCollector()

    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_node_list')
    def test_get_scoped_model_with_zones_pools_volumes(self, mock_zone_list):
        cluster = self.fake_cluster.generate_scenario_1()
        audit_scope = fake_scopes.fake_scope_2
        mock_zone_list.return_value = [
            mock.Mock(zone='zone_{0}'.format(i),
                      host='host_{0}@backend_{1}'.format(i, i))
            for i in range(2)]
        model = storage.StorageScope(audit_scope, mock.Mock(),
                                     osc=mock.Mock()).get_scoped_model(cluster)
        expected_edges = [(faker_cluster_state.volume_uuid_mapping['volume_0'],
                           'host_0@backend_0#pool_0'),
                          ('host_0@backend_0#pool_0', 'host_0@backend_0')]
        self.assertEqual(sorted(expected_edges), sorted(model.edges()))

    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_node_list')
    def test_get_scoped_model_without_scope(self, mock_zone_list):
        cluster = self.fake_cluster.generate_scenario_1()
        storage.StorageScope([], mock.Mock(),
                             osc=mock.Mock()).get_scoped_model(cluster)
        assert not mock_zone_list.called

    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_node_list')
    def test_collect_zones(self, mock_zone_list):
        allowed_nodes = []
        az_scope = [{'name': 'zone_1'}]
        mock_zone_list.return_value = [
            mock.Mock(zone='zone_{0}'.format(i),
                      host='host_{0}@backend_{1}'.format(i, i))
            for i in range(2)]
        storage.StorageScope([{'availability _zones': az_scope}],
                             mock.Mock(), osc=mock.Mock())._collect_zones(
            az_scope, allowed_nodes)
        self.assertEqual(['host_1@backend_1'], sorted(allowed_nodes))

        # storage scope with az wildcard
        az_scope = [{'name': '*'}]
        del allowed_nodes[:]
        storage.StorageScope([{'availability _zones': az_scope}],
                             mock.Mock(), osc=mock.Mock())._collect_zones(
            az_scope, allowed_nodes)
        self.assertEqual(['host_0@backend_0', 'host_1@backend_1'],
                         sorted(allowed_nodes))

        # storage scope with az wildcard and other
        az_scope = [{'name': '*'}, {'name': 'zone_0'}]
        del allowed_nodes[:]
        scope_handler = storage.StorageScope(
            [{'availability _zones': az_scope}], mock.Mock(), osc=mock.Mock())
        self.assertRaises(exception.WildcardCharacterIsUsed,
                          scope_handler._collect_zones,
                          az_scope, allowed_nodes)

    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_node_list')
    @mock.patch.object(cinder_helper.CinderHelper,
                       'get_volume_type_by_backendname')
    def test_collect_vtype(self, mock_vt_list, mock_zone_list):
        allowed_nodes = []
        mock_zone_list.return_value = [
            mock.Mock(zone='zone_{0}'.format(i),
                      host='host_{0}@backend_{1}'.format(i, i))
            for i in range(2)]

        def side_effect(arg):
            if arg == 'backend_0':
                return ['type_0']
            else:
                return ['type_1']

        mock_vt_list.side_effect = side_effect

        vt_scope = [{'name': 'type_1'}]
        storage.StorageScope([{'volume_types': vt_scope}],
                             mock.Mock(), osc=mock.Mock())._collect_vtype(
            vt_scope, allowed_nodes)
        self.assertEqual(['host_1@backend_1'], sorted(allowed_nodes))

        # storage scope with vt wildcard
        vt_scope = [{'name': '*'}]
        del allowed_nodes[:]
        storage.StorageScope([{'volume_types': vt_scope}],
                             mock.Mock(), osc=mock.Mock())._collect_vtype(
            vt_scope, allowed_nodes)
        self.assertEqual(['host_0@backend_0', 'host_1@backend_1'],
                         sorted(allowed_nodes))

        # storage scope with vt wildcard and other
        vt_scope = [{'name': '*'}, {'name': 'type_0'}]
        del allowed_nodes[:]
        scope_handler = storage.StorageScope([{'volume_types': vt_scope}],
                                             mock.Mock(), osc=mock.Mock())
        self.assertRaises(exception.WildcardCharacterIsUsed,
                          scope_handler._collect_vtype,
                          vt_scope, allowed_nodes)

    def test_exclude_resources(self):
        pools_to_exclude = []
        projects_to_exclude = []
        volumes_to_exclude = []
        resources = [{'volumes': [{'uuid': 'VOLUME_1'},
                                  {'uuid': 'VOLUME_2'}]
                      },
                     {'storage_pools': [{'name': 'host_0@backend_0#pool_1'},
                                        {'name': 'host_1@backend_1#pool_1'}]
                      },
                     {'projects': [{'uuid': 'PROJECT_1'},
                                   {'uuid': 'PROJECT_2'},
                                   {'uuid': 'PROJECT_3'}]
                      }
                     ]
        storage.StorageScope(resources, mock.Mock(),
                             osc=mock.Mock()).exclude_resources(
            resources, pools=pools_to_exclude, projects=projects_to_exclude,
            volumes=volumes_to_exclude)
        self.assertEqual(['VOLUME_1', 'VOLUME_2'], volumes_to_exclude)
        self.assertEqual(['PROJECT_1', 'PROJECT_2', 'PROJECT_3'],
                         projects_to_exclude)
        self.assertEqual(['host_0@backend_0#pool_1',
                          'host_1@backend_1#pool_1'], pools_to_exclude)

    def test_exclude_volumes(self):
        cluster = self.fake_cluster.generate_scenario_1()
        exclude = [faker_cluster_state.volume_uuid_mapping['volume_0'],
                   faker_cluster_state.volume_uuid_mapping['volume_3'],
                   ]
        storage.StorageScope([], mock.Mock(),
                             osc=mock.Mock()).exclude_volumes(exclude,
                                                              cluster)
        self.assertNotIn(exclude[0], cluster.get_all_volumes().keys())
        self.assertNotIn(exclude[1], cluster.get_all_volumes().keys())

    def test_exclude_pools(self):
        cluster = self.fake_cluster.generate_scenario_1()
        exclude = ['host_0@backend_0#pool_0']
        node_name = (exclude[0].split('#'))[0]

        storage.StorageScope([], mock.Mock(),
                             osc=mock.Mock()).exclude_pools(exclude,
                                                            cluster)
        node = cluster.get_node_by_name(node_name)
        self.assertNotIn(exclude, cluster.get_node_pools(node))

    def test_exclude_projects(self):
        cluster = self.fake_cluster.generate_scenario_1()
        exclude = ['project_1', 'project_2']
        storage.StorageScope([], mock.Mock(),
                             osc=mock.Mock()).exclude_projects(exclude,
                                                               cluster)
        projects = []
        volumes = cluster.get_all_volumes()
        for volume_id in volumes:
            volume = volumes.get(volume_id)
            projects.append(volume.get('project_id'))
        self.assertNotIn(exclude[0], projects)
        self.assertNotIn(exclude[1], projects)

    def test_remove_nodes_from_model(self):
        cluster = self.fake_cluster.generate_scenario_1()
        nodes_to_remove = ['host_0@backend_0']
        storage.StorageScope([], mock.Mock(),
                             osc=mock.Mock()).remove_nodes_from_model(
            nodes_to_remove, cluster)
        self.assertEqual(['host_1@backend_1'],
                         list(cluster.get_all_storage_nodes()))

    @mock.patch.object(cinder_helper.CinderHelper, 'get_storage_node_list')
    def test_get_scoped_model_with_multi_scopes(self, mock_zone_list):
        cluster = self.fake_cluster.generate_scenario_1()
        # includes storage and compute scope
        audit_scope = []
        audit_scope.extend(fake_scopes.fake_scope_2)
        audit_scope.extend(fake_scopes.fake_scope_1)
        mock_zone_list.return_value = [
            mock.Mock(zone='zone_{0}'.format(i),
                      host='host_{0}@backend_{1}'.format(i, i))
            for i in range(2)]
        model = storage.StorageScope(audit_scope, mock.Mock(),
                                     osc=mock.Mock()).get_scoped_model(cluster)
        expected_edges = [(faker_cluster_state.volume_uuid_mapping['volume_0'],
                           'host_0@backend_0#pool_0'),
                          ('host_0@backend_0#pool_0', 'host_0@backend_0')]
        self.assertEqual(sorted(expected_edges), sorted(model.edges()))
