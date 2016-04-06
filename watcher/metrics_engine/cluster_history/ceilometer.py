# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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


from oslo_config import cfg
from watcher.common import ceilometer_helper

from watcher.metrics_engine.cluster_history import base

CONF = cfg.CONF


class CeilometerClusterHistory(base.BaseClusterHistory):
    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        super(CeilometerClusterHistory, self).__init__()
        self.ceilometer = ceilometer_helper.CeilometerHelper(osc=osc)

    def statistic_list(self, meter_name, query=None, period=None):
        return self.ceilometer.statistic_list(meter_name, query, period)

    def query_sample(self, meter_name, query, limit=1):
        return self.ceilometer.query_sample(meter_name, query, limit)

    def get_last_sample_values(self, resource_id, meter_name, limit=1):
        return self.ceilometer.get_last_sample_values(resource_id, meter_name,
                                                      limit)

    def statistic_aggregation(self, resource_id, meter_name, period,
                              aggregate='avg'):
        return self.ceilometer.statistic_aggregation(resource_id, meter_name,
                                                     period,
                                                     aggregate)
