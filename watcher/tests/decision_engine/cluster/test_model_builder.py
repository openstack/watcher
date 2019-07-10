# -*- encoding: utf-8 -*-
# Copyright (c) 2019 European Organization for Nuclear Research (CERN)
#
# Authors: Corne Lukken <info@dantalion.nl>
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

import mock

from oslo_config import cfg
from oslo_log import log

from watcher.common import nova_helper
from watcher.decision_engine.model.collector import nova
from watcher.tests import base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class TestModelBuilder(base.BaseTestCase):
    """Test the collector ModelBuilder

        Objects under test are preceded with t_ and mocked objects are preceded
        with m_ , additionally, patched objects are preceded with p_ no object
        under test should be created in setUp this can influence the results.
        """

    def setUp(self):
        super(TestModelBuilder, self).setUp()

    def test_check_model(self):
        """Initialize collector ModelBuilder and test check model"""

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope))

    def test_check_model_update_false(self):
        """Initialize check model with multiple identical scopes

        The seconds check_model should return false as the models are the same
        """

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope))
        self.assertFalse(t_nova_cluster._check_model_scope(m_scope))

    def test_check_model_update_true(self):
        """Initialize check model with multiple different scopes

        Since the models differ both should return True for the update flag
        """

        m_scope_one = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        m_scope_two = [{"compute": [
            {"host_aggregates": [{"id": 2}]},
            {"availability_zones": [{"name": "av_b"}]}
        ]}]

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope_one))
        self.assertTrue(t_nova_cluster._check_model_scope(m_scope_two))

    def test_merge_compute_scope(self):
        """"""

        m_scope_one = [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]

        m_scope_two = [
            {"host_aggregates": [{"id": 4}]},
            {"availability_zones": [{"name": "av_b"}]}
        ]

        reference = {'availability_zones':
                     [{'name': 'av_a'}, {'name': 'av_b'}],
                     'host_aggregates':
                     [{'id': 5}, {'id': 4}]}

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        t_nova_cluster._merge_compute_scope(m_scope_one)
        t_nova_cluster._merge_compute_scope(m_scope_two)

        self.assertEqual(reference, t_nova_cluster.model_scope)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_collect_aggregates(self, m_nova):
        """"""

        m_nova.return_value.get_aggregate_list.return_value = \
            [mock.Mock(id=1, name='example'),
             mock.Mock(id=5, name='example', hosts=['hostone', 'hosttwo'])]

        m_nova.return_value.get_compute_node_by_name.return_value = False

        m_scope = [{'id': 5}]

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        result = set()
        t_nova_cluster._collect_aggregates(m_scope, result)

        self.assertEqual(set(['hostone', 'hosttwo']), result)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_collect_zones(self, m_nova):
        """"""

        m_nova.return_value.get_service_list.return_value = \
            [mock.Mock(zone='av_b'),
             mock.Mock(zone='av_a', host='hostone')]

        m_nova.return_value.get_compute_node_by_name.return_value = False

        m_scope = [{'name': 'av_a'}]

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        result = set()
        t_nova_cluster._collect_zones(m_scope, result)

        self.assertEqual(set(['hostone']), result)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_add_physical_layer(self, m_nova):
        """"""

        m_nova.return_value.get_aggregate_list.return_value = \
            [mock.Mock(id=1, name='example'),
             mock.Mock(id=5, name='example', hosts=['hostone', 'hosttwo'])]

        m_nova.return_value.get_service_list.return_value = \
            [mock.Mock(zone='av_b', host='hostthree'),
             mock.Mock(zone='av_a', host='hostone')]

        m_nova.return_value.get_compute_node_by_name.return_value = False

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        t_nova_cluster.execute(m_scope)
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hostone', servers=True, detailed=True)
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hosttwo', servers=True, detailed=True)
        self.assertEqual(
            m_nova.return_value.get_compute_node_by_name.call_count, 2)

    @mock.patch.object(nova_helper, 'NovaHelper')
    def test_add_physical_layer_with_baremetal_node(self, m_nova):
        """"""

        m_nova.return_value.get_aggregate_list.return_value = \
            [mock.Mock(id=1, name='example'),
             mock.Mock(id=5, name='example', hosts=['hostone', 'hosttwo'])]

        m_nova.return_value.get_service_list.return_value = \
            [mock.Mock(zone='av_b', host='hostthree'),
             mock.Mock(zone='av_a', host='hostone')]

        compute_node = mock.Mock(
            id='796fee99-65dd-4262-aa-fd2a1143faa6',
            hypervisor_hostname='hostone',
            hypervisor_type='QEMU',
            state='TEST_STATE',
            status='TEST_STATUS',
            memory_mb=333,
            free_disk_gb=222,
            local_gb=111,
            vcpus=4,
            servers=[
                {'name': 'fake_instance',
                 'uuid': 'ef500f7e-dac8-470f-960c-169486fce71b'}
            ],
            service={'id': 123, 'host': 'hostone',
                     'disabled_reason': ''},
        )

        baremetal_node = mock.Mock(
            id='5f2d1b3d-4099-4623-b9-05148aefd6cb',
            hypervisor_hostname='hosttwo',
            hypervisor_type='ironic',
            state='TEST_STATE',
            status='TEST_STATUS',
        )

        m_nova.return_value.get_compute_node_by_name.side_effect = [
            [compute_node], [baremetal_node]]

        m_scope = [{"compute": [
            {"host_aggregates": [{"id": 5}]},
            {"availability_zones": [{"name": "av_a"}]}
        ]}]

        t_nova_cluster = nova.ModelBuilder(mock.Mock())
        model = t_nova_cluster.execute(m_scope)

        compute_nodes = model.get_all_compute_nodes()
        self.assertEqual(1, len(compute_nodes))
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hostone', servers=True, detailed=True)
        m_nova.return_value.get_compute_node_by_name.assert_any_call(
            'hosttwo', servers=True, detailed=True)
        self.assertEqual(
            m_nova.return_value.get_compute_node_by_name.call_count, 2)
