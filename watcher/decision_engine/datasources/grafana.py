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
import six.moves.urllib.parse as urlparse

from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.datasources import base
from watcher.decision_engine.datasources.grafana_translator import influxdb

import requests

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class GrafanaHelper(base.DataSourceBase):

    NAME = 'grafana'

    """METRIC_MAP is only available at runtime _build_metric_map"""
    METRIC_MAP = dict()

    """All available translators"""
    TRANSLATOR_LIST = [
        influxdb.InfluxDBGrafanaTranslator.NAME
    ]

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.nova = self.osc.nova()
        self.configured = False
        self._base_url = None
        self._headers = None
        self._setup()

    def _setup(self):
        """Configure grafana helper to perform requests"""

        token = CONF.grafana_client.token
        base_url = CONF.grafana_client.base_url

        if not token:
            LOG.critical("GrafanaHelper authentication token not configured")
            return
        self._headers = {"Authorization": "Bearer " + token,
                         "Content-Type": "Application/json"}

        if not base_url:
            LOG.critical("GrafanaHelper url not properly configured, "
                         "check base_url")
            return
        self._base_url = base_url

        # Very basic url parsing
        parse = urlparse.urlparse(self._base_url)
        if parse.scheme is '' or parse.netloc is '' or parse.path is '':
            LOG.critical("GrafanaHelper url not properly configured, "
                         "check base_url and project_id")
            return

        self._build_metric_map()

        if len(self.METRIC_MAP) == 0:
            LOG.critical("GrafanaHelper not configured for any metrics")

        self.configured = True

    def _build_metric_map(self):
        """Builds the metric map by reading config information"""

        for key, value in CONF.grafana_client.database_map.items():
            try:
                project = CONF.grafana_client.project_id_map[key]
                attribute = CONF.grafana_client.attribute_map[key]
                translator = CONF.grafana_client.translator_map[key]
                query = CONF.grafana_client.query_map[key]
                if project is not None and \
                   value is not None and\
                   translator in self.TRANSLATOR_LIST and\
                   query is not None:
                    self.METRIC_MAP[key] = {
                        'db': value,
                        'project': project,
                        'attribute': attribute,
                        'translator': translator,
                        'query': query
                    }
            except KeyError as e:
                LOG.error(e)

    def _build_translator_schema(self, metric, db, attribute, query, resource,
                                 resource_type, period, aggregate,
                                 granularity):
        """Create dictionary to pass to grafana proxy translators"""

        return {'metric': metric, 'db': db, 'attribute': attribute,
                'query': query, 'resource': resource,
                'resource_type': resource_type, 'period': period,
                'aggregate': aggregate, 'granularity': granularity}

    def _get_translator(self, name, data):
        """Use the names of translators to get the translator for the metric"""
        if name == influxdb.InfluxDBGrafanaTranslator.NAME:
            return influxdb.InfluxDBGrafanaTranslator(data)
        else:
            raise exception.InvalidParameter(
                parameter='name', parameter_type='grafana translator')

    def _request(self, params, project_id):
        """Make the request to the endpoint to retrieve data

        If the request fails, determines what error to raise.
        """

        if self.configured is False:
            raise exception.DataSourceNotAvailable(self.NAME)

        resp = requests.get(self._base_url + str(project_id) + '/query',
                            params=params, headers=self._headers)
        if resp.status_code == 200:
            return resp
        elif resp.status_code == 400:
            LOG.error("Query for metric is invalid")
        elif resp.status_code == 401:
            LOG.error("Authorization token is invalid")
        raise exception.DataSourceNotAvailable(self.NAME)

    def statistic_aggregation(self, resource=None, resource_type=None,
                              meter_name=None, period=300, aggregate='mean',
                              granularity=300):
        """Get the value for the specific metric based on specified parameters

        """

        try:
            self.METRIC_MAP[meter_name]
        except KeyError:
            LOG.error("Metric: {0} does not appear in the current Grafana "
                      "metric map".format(meter_name))
            raise exception.MetricNotAvailable(metric=meter_name)

        db = self.METRIC_MAP[meter_name]['db']
        project = self.METRIC_MAP[meter_name]['project']
        attribute = self.METRIC_MAP[meter_name]['attribute']
        translator_name = self.METRIC_MAP[meter_name]['translator']
        query = self.METRIC_MAP[meter_name]['query']

        data = self._build_translator_schema(
            meter_name, db, attribute, query, resource, resource_type, period,
            aggregate, granularity)

        translator = self._get_translator(translator_name, data)

        params = translator.build_params()

        raw_kwargs = dict(
            params=params,
            project_id=project,
        )
        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        resp = self.query_retry(self._request, **kwargs)
        if not resp:
            LOG.warning("Datasource {0} is not available.".format(self.NAME))
            return

        result = translator.extract_result(resp.content)

        return result

    def get_host_cpu_usage(self, resource, period=300,
                           aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'compute_node', 'host_cpu_usage', period, aggregate,
            granularity)

    def get_host_ram_usage(self, resource, period=300,
                           aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'compute_node', 'host_ram_usage', period, aggregate,
            granularity)

    def get_host_outlet_temp(self, resource, period=300,
                             aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'compute_node', 'host_outlet_temp', period, aggregate,
            granularity)

    def get_host_inlet_temp(self, resource, period=300,
                            aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'compute_node', 'host_inlet_temp', period, aggregate,
            granularity)

    def get_host_airflow(self, resource, period=300,
                         aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'compute_node', 'host_airflow', period, aggregate,
            granularity)

    def get_host_power(self, resource, period=300,
                       aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'compute_node', 'host_power', period, aggregate,
            granularity)

    def get_instance_cpu_usage(self, resource, period=300,
                               aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'instance', 'instance_cpu_usage', period, aggregate,
            granularity)

    def get_instance_ram_usage(self, resource, period=300,
                               aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'instance', 'instance_ram_usage', period, aggregate,
            granularity)

    def get_instance_ram_allocated(self, resource, period=300,
                                   aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'instance', 'instance_ram_allocated', period, aggregate,
            granularity)

    def get_instance_l3_cache_usage(self, resource, period=300,
                                    aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'instance', 'instance_l3_cache_usage', period, aggregate,
            granularity)

    def get_instance_root_disk_size(self, resource, period=300,
                                    aggregate="mean", granularity=None):
        return self.statistic_aggregation(
            resource, 'instance', 'instance_root_disk_size', period, aggregate,
            granularity)
