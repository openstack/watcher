# -*- encoding: utf-8 -*-
# Copyright (c) 2018 SBCloud
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

from unittest import mock

from watcher.decision_engine.scope import baremetal
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.scope import fake_scopes


class TestBaremetalScope(base.TestCase):

    def setUp(self):
        super(TestBaremetalScope, self).setUp()
        self.fake_cluster = faker_cluster_state.FakerBaremetalModelCollector()
        self.audit_scope = fake_scopes.baremetal_scope

    def test_exclude_all_ironic_nodes(self):
        cluster = self.fake_cluster.generate_scenario_1()
        baremetal.BaremetalScope(
            self.audit_scope,
            mock.Mock(),
            osc=mock.Mock()).get_scoped_model(cluster)

        self.assertEqual({}, cluster.get_all_ironic_nodes())

    def test_exclude_resources(self):
        nodes_to_exclude = []
        resources = fake_scopes.baremetal_scope[0]['baremetal'][0]['exclude']
        baremetal.BaremetalScope(
            self.audit_scope, mock.Mock(), osc=mock.Mock()).exclude_resources(
                resources,
                nodes=nodes_to_exclude)

        self.assertEqual(sorted(nodes_to_exclude),
                         sorted(['c5941348-5a87-4016-94d4-4f9e0ce2b87a',
                                 'c5941348-5a87-4016-94d4-4f9e0ce2b87c']))

    def test_remove_nodes_from_model(self):
        cluster = self.fake_cluster.generate_scenario_1()
        baremetal.BaremetalScope(
            self.audit_scope,
            mock.Mock(),
            osc=mock.Mock()).remove_nodes_from_model(
                ['c5941348-5a87-4016-94d4-4f9e0ce2b87a'],
                cluster)
        self.assertEqual(len(cluster.get_all_ironic_nodes()), 1)
