# -*- encoding: utf-8 -*-
# Copyright (c) 2019 European Organization for Nuclear Research (CERN)
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

from unittest import mock

from watcher.common import exception
from watcher.decision_engine.datasources import manager
from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state


class TestBaseStrategy(base.TestCase):

    def setUp(self):
        super(TestBaseStrategy, self).setUp()

        # fake cluster
        self.fake_c_cluster = faker_cluster_state.FakerModelCollector()

        p_c_model = mock.patch.object(
            strategies.BaseStrategy, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_c_model = p_c_model.start()
        self.addCleanup(p_c_model.stop)

        p_audit_scope = mock.patch.object(
            strategies.BaseStrategy, "audit_scope",
            new_callable=mock.PropertyMock)
        self.m_audit_scope = p_audit_scope.start()
        self.addCleanup(p_audit_scope.stop)

        self.m_audit_scope.return_value = mock.Mock()

        self.m_c_model.return_value = model_root.ModelRoot()
        self.strategy = strategies.DummyStrategy(config=mock.Mock())


class TestBaseStrategyDatasource(TestBaseStrategy):

    def setUp(self):
        super(TestBaseStrategyDatasource, self).setUp()
        self.strategy = strategies.DummyStrategy(
            config=mock.Mock(datasources=None))

    @mock.patch.object(strategies.BaseStrategy, 'osc', None)
    @mock.patch.object(manager, 'DataSourceManager')
    @mock.patch.object(strategies.base, 'CONF')
    def test_global_preference(self, m_conf, m_manager):
        """Test if the global preference is used"""

        m_conf.watcher_datasources.datasources = \
            ['gnocchi', 'monasca', 'ceilometer']

        # Make sure we access the property and not the underlying function.
        m_manager.return_value.get_backend.return_value = \
            mock.NonCallableMock()

        # Access the property so that the configuration is read in order to
        # get the correct datasource
        self.strategy.datasource_backend

        m_manager.assert_called_once_with(
            config=m_conf.watcher_datasources, osc=None)

    @mock.patch.object(strategies.BaseStrategy, 'osc', None)
    @mock.patch.object(manager, 'DataSourceManager')
    @mock.patch.object(strategies.base, 'CONF')
    def test_global_preference_reverse(self, m_conf, m_manager):
        """Test if the global preference is used with another order"""

        m_conf.watcher_datasources.datasources = \
            ['ceilometer', 'monasca', 'gnocchi']

        # Make sure we access the property and not the underlying function.
        m_manager.return_value.get_backend.return_value = \
            mock.NonCallableMock()

        # Access the property so that the configuration is read in order to
        # get the correct datasource
        self.strategy.datasource_backend

        m_manager.assert_called_once_with(
            config=m_conf.watcher_datasources, osc=None)

    @mock.patch.object(strategies.BaseStrategy, 'osc', None)
    @mock.patch.object(manager, 'DataSourceManager')
    @mock.patch.object(strategies.base, 'CONF')
    def test_strategy_preference_override(self, m_conf, m_manager):
        """Test if the global preference can be overridden"""

        datasources = mock.Mock(datasources=['ceilometer'])

        self.strategy = strategies.DummyStrategy(
            config=datasources)

        m_conf.watcher_datasources.datasources = \
            ['ceilometer', 'monasca', 'gnocchi']

        # Access the property so that the configuration is read in order to
        # get the correct datasource
        self.strategy.datasource_backend

        m_manager.assert_called_once_with(
            config=datasources, osc=None)


class TestBaseStrategyException(TestBaseStrategy):

    def setUp(self):
        super(TestBaseStrategyException, self).setUp()

    def test_exception_model(self):
        self.m_c_model.return_value = None
        self.assertRaises(
            exception.ClusterStateNotDefined, self.strategy.execute)

    def test_exception_stale_cdm(self):
        self.fake_c_cluster.set_cluster_data_model_as_stale()
        self.m_c_model.return_value = self.fake_c_cluster.cluster_data_model

        self.assertRaises(
            # TODO(Dantali0n) This should return ClusterStale,
            #  improve set_cluster_data_model_as_stale().
            exception.ClusterStateNotDefined,
            self.strategy.execute)
