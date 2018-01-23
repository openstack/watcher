# -*- encoding: utf-8 -*-
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

from oslo_log import log

from watcher.common import exception
from watcher.datasource import base
from watcher.datasource import ceilometer as ceil
from watcher.datasource import gnocchi as gnoc
from watcher.datasource import monasca as mon

LOG = log.getLogger(__name__)


class DataSourceManager(object):

    def __init__(self, config=None, osc=None):
        self.osc = osc
        self.config = config
        self._ceilometer = None
        self._monasca = None
        self._gnocchi = None
        self.metric_map = base.DataSourceBase.METRIC_MAP
        self.datasources = self.config.datasources

    @property
    def ceilometer(self):
        if self._ceilometer is None:
            self.ceilometer = ceil.CeilometerHelper(osc=self.osc)
        return self._ceilometer

    @ceilometer.setter
    def ceilometer(self, ceilometer):
        self._ceilometer = ceilometer

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

    def get_backend(self, metrics):
        for datasource in self.datasources:
            no_metric = False
            for metric in metrics:
                if (metric not in self.metric_map[datasource] or
                   self.metric_map[datasource].get(metric) is None):
                        no_metric = True
                        break
            if not no_metric:
                return getattr(self, datasource)
        raise exception.NoSuchMetric()
