# Copyright 2017 NEC Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import yaml

from collections import OrderedDict
from oslo_config import cfg
from oslo_log import log

from watcher.common import exception
from watcher.decision_engine.datasources import aetos
from watcher.decision_engine.datasources import gnocchi as gnoc
from watcher.decision_engine.datasources import grafana as graf
from watcher.decision_engine.datasources import monasca as mon
from watcher.decision_engine.datasources import prometheus as prom

LOG = log.getLogger(__name__)


class DataSourceManager:

    metric_map = OrderedDict([
        (gnoc.GnocchiHelper.NAME, gnoc.GnocchiHelper.METRIC_MAP),
        (mon.MonascaHelper.NAME, mon.MonascaHelper.METRIC_MAP),
        (graf.GrafanaHelper.NAME, graf.GrafanaHelper.METRIC_MAP),
        (prom.PrometheusHelper.NAME, prom.PrometheusHelper.METRIC_MAP),
        (aetos.AetosHelper.NAME, aetos.AetosHelper.METRIC_MAP),
    ])
    """Dictionary with all possible datasources, dictionary order is
    the default order for attempting to use datasources
    """

    def __init__(self, config=None, osc=None):
        self.osc = osc
        self.config = config
        self._monasca = None
        self._gnocchi = None
        self._grafana = None
        self._prometheus = None
        self._aetos = None

        # Dynamically update grafana metric map, only available at runtime
        # The metric map can still be overridden by a yaml config file
        self.metric_map[graf.GrafanaHelper.NAME] = self.grafana.METRIC_MAP

        metric_map_path = cfg.CONF.watcher_decision_engine.metric_map_path
        metrics_from_file = self.load_metric_map(metric_map_path)
        for ds, mp in self.metric_map.items():
            try:
                self.metric_map[ds].update(metrics_from_file.get(ds, {}))
            except KeyError:
                msgargs = (ds, self.metric_map.keys())
                LOG.warning('Invalid Datasource: %s. Allowed: %s ', *msgargs)

        self.datasources = self.config.datasources
        if self.datasources and 'monasca' in self.datasources:
            LOG.warning('The monasca datasource is deprecated and will be '
                        'removed in a future release.')

        self._validate_datasource_config()

    def _validate_datasource_config(self):
        """Validate datasource configuration

        Checks for configuration conflicts, such as having both prometheus
        and aetos datasources configured simultaneously.
        """
        if (self.datasources and
                prom.PrometheusHelper.NAME in self.datasources and
                aetos.AetosHelper.NAME in self.datasources):
            LOG.error("Configuration error: Cannot use both prometheus "
                      "and aetos datasources simultaneously.")
            raise exception.DataSourceConfigConflict(
                datasource_one=prom.PrometheusHelper.NAME,
                datasource_two=aetos.AetosHelper.NAME
            )

    @property
    def monasca(self):
        if self._monasca is None:
            self._monasca = mon.MonascaHelper(osc=self.osc)
        return self._monasca

    @monasca.setter
    def monasca(self, monasca):
        self._monasca = monasca

    @property
    def gnocchi(self):
        if self._gnocchi is None:
            self._gnocchi = gnoc.GnocchiHelper(osc=self.osc)
        return self._gnocchi

    @gnocchi.setter
    def gnocchi(self, gnocchi):
        self._gnocchi = gnocchi

    @property
    def grafana(self):
        if self._grafana is None:
            self._grafana = graf.GrafanaHelper(osc=self.osc)
        return self._grafana

    @grafana.setter
    def grafana(self, grafana):
        self._grafana = grafana

    @property
    def prometheus(self):
        if self._prometheus is None:
            self._prometheus = prom.PrometheusHelper()
        return self._prometheus

    @prometheus.setter
    def prometheus(self, prometheus):
        self._prometheus = prometheus

    @property
    def aetos(self):
        if self._aetos is None:
            self._aetos = aetos.AetosHelper(osc=self.osc)
        return self._aetos

    @aetos.setter
    def aetos(self, aetos):
        self._aetos = aetos

    def get_backend(self, metrics):
        """Determine the datasource to use from the configuration

        Iterates over the configured datasources in order to find the first
        which can support all specified metrics. Upon a missing metric the next
        datasource is attempted.
        """

        if not self.datasources or len(self.datasources) == 0:
            raise exception.NoDatasourceAvailable

        if not metrics or len(metrics) == 0:
            LOG.critical("Can not retrieve datasource without specifying "
                         "list of required metrics.")
            raise exception.InvalidParameter(parameter='metrics',
                                             parameter_type='none empty list')

        for datasource in self.datasources:
            # Skip configured datasources that are not available at runtime
            if datasource not in self.metric_map:
                LOG.warning(
                    "Datasource: %s is not available; skipping.",
                    datasource,
                )
                continue
            no_metric = False
            for metric in metrics:
                if (metric not in self.metric_map[datasource] or
                        self.metric_map[datasource].get(metric) is None):
                    no_metric = True
                    LOG.warning(
                        "Datasource: %s could not be used due to metric: %s",
                        datasource,
                        metric,
                    )
                    break
            if not no_metric:
                # Try to use a specific datasource but attempt additional
                # datasources upon exceptions (if config has more datasources)
                try:
                    ds = getattr(self, datasource)
                    ds.METRIC_MAP.update(self.metric_map[ds.NAME])
                    return ds
                except Exception:
                    pass  # nosec: B110
        raise exception.MetricNotAvailable(metric=metric)

    def load_metric_map(self, file_path):
        """Load metrics from the metric_map_path"""
        if file_path and os.path.exists(file_path):
            with open(file_path) as f:
                try:
                    ret = yaml.safe_load(f.read())
                    # return {} if the file is empty
                    return ret if ret else {}
                except yaml.YAMLError as e:
                    LOG.warning('Could not load %s: %s', file_path, e)
                return {}
        else:
            return {}
