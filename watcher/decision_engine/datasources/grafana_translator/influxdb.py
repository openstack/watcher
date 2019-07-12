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

from oslo_config import cfg
from oslo_log import log
from oslo_serialization import jsonutils

from watcher.common import exception
from watcher.decision_engine.datasources.grafana_translator.base import \
    BaseGrafanaTranslator

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class InfluxDBGrafanaTranslator(BaseGrafanaTranslator):
    """Grafana translator to communicate with InfluxDB database"""

    NAME = 'influxdb'

    def __init__(self, data):
        super(InfluxDBGrafanaTranslator, self).__init__(data)

    def build_params(self):
        """"""

        data = self._data

        retention_period = None
        available_periods = CONF.grafana_translators.retention_periods.items()
        for key, value in sorted(available_periods, key=lambda x: x[1]):
            if int(data['period']) < int(value):
                retention_period = key
                break

        if retention_period is None:
            retention_period = max(available_periods)[0]
            LOG.warning("Longest retention period is to short for desired"
                        " period")

        try:
            resource = self._extract_attribute(
                data['resource'], data['attribute'])
        except AttributeError:
            LOG.error("Resource: {0} does not contain attribute {1}".format(
                data['resource'], data['attribute']))
            raise

        # Granularity is optional if it is None the minimal value for InfluxDB
        # will be 1
        granularity = \
            data['granularity'] if data['granularity'] is not None else 1

        return {'db': data['db'],
                'epoch': 'ms',
                'q': self._query_format(
                    data['query'], data['aggregate'], resource, data['period'],
                    granularity, retention_period)}

    def extract_result(self, raw_results):
        """"""
        try:
            # For result structure see:
            # https://docs.openstack.org/watcher/latest/datasources/grafana.html#InfluxDB
            result = jsonutils.loads(raw_results)
            result = result['results'][0]['series'][0]
            index_aggregate = result['columns'].index(self._data['aggregate'])
            return result['values'][0][index_aggregate]
        except KeyError:
            LOG.error("Could not extract {0} for the resource: {1}".format(
                self._data['metric'], self._data['resource']))
            raise exception.NoSuchMetricForHost(
                metric=self._data['metric'], host=self._data['resource'])
