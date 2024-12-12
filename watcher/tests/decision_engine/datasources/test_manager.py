# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
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

from unittest.mock import MagicMock

from watcher.common import exception
from watcher.decision_engine.datasources import gnocchi
from watcher.decision_engine.datasources import grafana
from watcher.decision_engine.datasources import manager as ds_manager
from watcher.decision_engine.datasources import monasca
from watcher.tests import base


class TestDataSourceManager(base.BaseTestCase):

    def _dsm_config(self, **kwargs):
        dss = ['gnocchi', 'monasca']
        opts = dict(datasources=dss, metric_map_path=None)
        opts.update(kwargs)
        return MagicMock(**opts)

    def _dsm(self, **kwargs):
        opts = dict(config=self._dsm_config(), osc=mock.MagicMock())
        opts.update(kwargs)
        return ds_manager.DataSourceManager(**opts)

    def test_metric_file_path_not_exists(self):
        manager = self._dsm()
        expected = ds_manager.DataSourceManager.metric_map
        actual = manager.metric_map
        self.assertEqual(expected, actual)
        self.assertEqual({}, manager.load_metric_map('/nope/nope/nope.yaml'))

    def test_metric_file_metric_override(self):
        path = 'watcher.decision_engine.datasources.manager.' \
               'DataSourceManager.load_metric_map'
        retval = {
            monasca.MonascaHelper.NAME: {"host_airflow": "host_fnspid"}
        }
        with mock.patch(path, return_value=retval):
            dsmcfg = self._dsm_config(datasources=['monasca'])
            manager = self._dsm(config=dsmcfg)
            backend = manager.get_backend(['host_airflow'])
            self.assertEqual("host_fnspid", backend.METRIC_MAP['host_airflow'])

    @mock.patch.object(grafana, 'CONF')
    def test_metric_file_metric_override_grafana(self, m_config):
        """Grafana requires a different structure in the metric map"""

        m_config.grafana_client.token = \
            "eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk=="
        m_config.grafana_client.base_url = "https://grafana.proxy/api/"

        path = 'watcher.decision_engine.datasources.manager.' \
               'DataSourceManager.load_metric_map'
        metric_map = {
            'db': 'production_cloud',
            'project': '7485',
            'attribute': 'hostname',
            'translator': 'influxdb',
            'query': 'SHOW SERIES'
        }
        retval = {
            grafana.GrafanaHelper.NAME: {"host_airflow": metric_map}
        }
        with mock.patch(path, return_value=retval):
            dsmcfg = self._dsm_config(datasources=['grafana'])
            manager = self._dsm(config=dsmcfg)
            backend = manager.get_backend(['host_airflow'])
            self.assertEqual(metric_map, backend.METRIC_MAP['host_airflow'])

    def test_metric_file_invalid_ds(self):
        with mock.patch('yaml.safe_load') as mo:
            mo.return_value = {"newds": {"metric_one": "i_am_metric_one"}}
            mgr = self._dsm()
            self.assertNotIn('newds', mgr.metric_map.keys())

    def test_get_backend(self):
        manager = self._dsm()
        backend = manager.get_backend(['host_cpu_usage', 'instance_cpu_usage'])
        self.assertEqual(backend, manager.gnocchi)

    def test_get_backend_order(self):
        dss = ['monasca', 'gnocchi']
        dsmcfg = self._dsm_config(datasources=dss)
        manager = self._dsm(config=dsmcfg)
        backend = manager.get_backend(['host_cpu_usage', 'instance_cpu_usage'])
        self.assertEqual(backend, manager.monasca)

    def test_get_backend_wrong_metric(self):
        manager = self._dsm()
        self.assertRaises(exception.MetricNotAvailable, manager.get_backend,
                          ['host_cpu', 'instance_cpu_usage'])

    @mock.patch.object(gnocchi, 'GnocchiHelper')
    def test_get_backend_error_datasource(self, m_gnocchi):
        m_gnocchi.side_effect = exception.DataSourceNotAvailable
        manager = self._dsm()
        backend = manager.get_backend(['host_cpu_usage', 'instance_cpu_usage'])
        self.assertEqual(backend, manager.monasca)

    @mock.patch.object(grafana.GrafanaHelper, 'METRIC_MAP',
                       {'host_cpu_usage': 'test'})
    def test_get_backend_grafana(self):
        dss = ['grafana', 'gnocchi']
        dsmcfg = self._dsm_config(datasources=dss)
        manager = self._dsm(config=dsmcfg)
        backend = manager.get_backend(['host_cpu_usage'])
        self.assertEqual(backend, manager.grafana)

    @mock.patch.object(grafana, 'CONF')
    def test_dynamic_metric_map_grafana(self, m_config):
        m_config.grafana_client.token = \
            "eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk=="
        m_config.grafana_client.base_url = "https://grafana.proxy/api/"
        m_config.grafana_client.project_id_map = {'host_cpu_usage': 7221}
        m_config.grafana_client.attribute_map = {'host_cpu_usage': 'hostname'}
        m_config.grafana_client.database_map = {'host_cpu_usage': 'mock_db'}
        m_config.grafana_client.translator_map = {'host_cpu_usage': 'influxdb'}
        m_config.grafana_client.query_map = {
            'host_cpu_usage': 'SHOW SERIES'
        }
        dss = ['grafana', 'gnocchi']
        dsmcfg = self._dsm_config(datasources=dss)
        manager = self._dsm(config=dsmcfg)
        backend = manager.get_backend(['host_cpu_usage'])
        self.assertEqual(backend, manager.grafana)

    def test_get_backend_no_datasources(self):
        dsmcfg = self._dsm_config(datasources=[])
        manager = self._dsm(config=dsmcfg)
        self.assertRaises(exception.NoDatasourceAvailable, manager.get_backend,
                          ['host_cpu_usage', 'instance_cpu_usage'])
        dsmcfg = self._dsm_config(datasources=None)
        manager = self._dsm(config=dsmcfg)
        self.assertRaises(exception.NoDatasourceAvailable, manager.get_backend,
                          ['host_cpu_usage', 'instance_cpu_usage'])

    def test_get_backend_no_metrics(self):
        manager = self._dsm()
        self.assertRaises(exception.InvalidParameter, manager.get_backend, [])
        self.assertRaises(exception.InvalidParameter, manager.get_backend,
                          None)
