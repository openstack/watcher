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

import copy
import mock

from oslo_config import cfg
from oslo_log import log

from watcher.common import exception
from watcher.decision_engine.datasources.grafana_translator import influxdb
from watcher.tests.decision_engine.datasources.grafana_translators import \
    test_base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class TestInfluxDBGrafanaTranslator(test_base.TestGrafanaTranslatorBase):
    """Test the InfluxDB gragana database translator

    Objects under test are preceded with t_ and mocked objects are preceded
    with m_ , additionally, patched objects are preceded with p_ no object
    under test should be created in setUp this can influence the results.
    """

    def setUp(self):
        super(TestInfluxDBGrafanaTranslator, self).setUp()

        self.p_conf = mock.patch.object(
            influxdb, 'CONF',
            new_callable=mock.PropertyMock)
        self.m_conf = self.p_conf.start()
        self.addCleanup(self.p_conf.stop)

        self.m_conf.grafana_translators.retention_periods = {
            'one_day': 86400,
            'one_week': 604800
        }

    def test_retention_period_one_day(self):
        """Validate lowest retention period"""

        data = copy.copy(self.reference_data)
        data['query'] = "{4}"

        t_influx = influxdb.InfluxDBGrafanaTranslator(
            data=data)
        params = t_influx.build_params()
        self.assertEqual(params['q'], 'one_day')

    def test_retention_period_one_week(self):
        """Validate incrementing retention periods"""

        data = copy.copy(self.reference_data)
        data['query'] = "{4}"

        data['period'] = 90000
        t_influx = influxdb.InfluxDBGrafanaTranslator(
            data=data)
        params = t_influx.build_params()
        self.assertEqual(params['q'], 'one_week')

    @mock.patch.object(influxdb, 'LOG')
    def test_retention_period_warning(self, m_log):
        """Validate retention period warning"""

        data = copy.copy(self.reference_data)
        data['query'] = "{4}"

        data['period'] = 650000
        t_influx = influxdb.InfluxDBGrafanaTranslator(
            data=data)
        params = t_influx.build_params()
        self.assertEqual(params['q'], 'one_week')
        m_log.warning.assert_called_once_with(
            "Longest retention period is to short for desired period")

    def test_build_params_granularity(self):
        """Validate build params granularity"""

        data = copy.copy(self.reference_data)
        data['granularity'] = None
        data['query'] = "{3}"

        t_influx = influxdb.InfluxDBGrafanaTranslator(
            data=data)

        raw_results = {
            'db': 'production',
            'epoch': 'ms',
            'q': '1'
        }

        # InfluxDB build_params should replace granularity None optional with 1
        result = t_influx.build_params()

        self.assertEqual(raw_results, result)

    def test_build_params_order(self):
        """Validate order of build params"""

        data = copy.copy(self.reference_data)
        data['aggregate'] = 'count'
        # prevent having to deepcopy by keeping this value the same
        # this will access the value 'hyperion' from the mocked resource object
        data['attribute'] = 'hostname'
        data['period'] = 3
        # because the period is only 3 the retention_period will be one_day
        data['granularity'] = 4
        data['query'] = "{0}{1}{2}{3}{4}"

        t_influx = influxdb.InfluxDBGrafanaTranslator(
            data=data)

        raw_results = "counthyperion34one_day"

        result = t_influx.build_params()

        self.assertEqual(raw_results, result['q'])

    def test_extract_results(self):
        """Validate proper result extraction"""

        t_influx = influxdb.InfluxDBGrafanaTranslator(
            data=self.reference_data)

        raw_results = "{ \"results\": [{ \"series\": [{ " \
                      "\"columns\": [\"time\",\"mean\"]," \
                      "\"values\": [[1552500855000, " \
                      "67.3550078657577]]}]}]}"

        # Structure of InfluxDB time series data
        # { "results": [{
        #             "statement_id": 0,
        #             "series": [{
        #                     "name": "cpu_percent",
        #                     "columns": [
        #                         "time",
        #                         "mean"
        #                     ],
        #                     "values": [[
        #                         1552500855000,
        #                         67.3550078657577
        #                     ]]
        #                 }]
        # }]}

        self.assertEqual(t_influx.extract_result(raw_results),
                         67.3550078657577)

    def test_extract_results_error(self):
        """Validate error on missing results"""

        t_influx = influxdb.InfluxDBGrafanaTranslator(
            data=self.reference_data)

        raw_results = "{}"

        self.assertRaises(exception.NoSuchMetricForHost,
                          t_influx.extract_result, raw_results)
