# -*- encoding: utf-8 -*-
# Copyright (c) 2018 Servionica
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

from watcher.decision_engine.strategy.strategies import base as strategy_base
from watcher.tests import base


class TestStrategyEndpoint(base.BaseTestCase):

    def test_collect_metrics(self):
        datasource = mock.MagicMock()
        datasource.list_metrics.return_value = ["m1", "m2"]
        datasource.METRIC_MAP = {"metric1": "m1", "metric2": "m2",
                                 "metric3": "m3"}
        strategy = mock.MagicMock()
        strategy.DATASOURCE_METRICS = ["metric1", "metric2", "metric3"]
        strategy.config.datasource = "gnocchi"
        se = strategy_base.StrategyEndpoint(mock.MagicMock())
        result = se._collect_metrics(strategy, datasource)
        expected_result = {'type': 'Metrics',
                           'state': [{"m1": "available"},
                                     {"m2": "available"},
                                     {"m3": "not available"}],
                           'mandatory': False, 'comment': ''}
        self.assertEqual(expected_result, result)

    def test_get_datasource_status(self):
        strategy = mock.MagicMock()
        datasource = mock.MagicMock()
        datasource.NAME = 'gnocchi'
        datasource.check_availability.return_value = "available"
        se = strategy_base.StrategyEndpoint(mock.MagicMock())
        result = se._get_datasource_status(strategy, datasource)
        expected_result = {'type': 'Datasource',
                           'state': "gnocchi: available",
                           'mandatory': True, 'comment': ''}
        self.assertEqual(expected_result, result)

    def test_get_cdm(self):
        strategy = mock.MagicMock()
        strategy.compute_model = mock.MagicMock()
        del strategy.storage_model
        strategy.baremetal_model = mock.MagicMock()
        se = strategy_base.StrategyEndpoint(mock.MagicMock())
        result = se._get_cdm(strategy)
        expected_result = {'type': 'CDM',
                           'state': [{"compute_model": "available"},
                                     {"storage_model": "not available"},
                                     {"baremetal_model": "available"}],
                           'mandatory': True, 'comment': ''}
        self.assertEqual(expected_result, result)
