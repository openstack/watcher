# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
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

from datetime import datetime
import time

from oslo_config import cfg
from oslo_log import log

from watcher.common import clients
from watcher.common import exception

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class GnocchiHelper(object):

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.gnocchi = self.osc.gnocchi()

    def query_retry(self, f, *args, **kwargs):
        for i in range(CONF.gnocchi_client.query_max_retries):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                LOG.exception(e)
                time.sleep(CONF.gnocchi_client.query_timeout)
        raise

    def statistic_aggregation(self,
                              resource_id,
                              metric,
                              granularity,
                              start_time=None,
                              stop_time=None,
                              aggregation='mean'):
        """Representing a statistic aggregate by operators

        :param metric: metric name of which we want the statistics
        :param resource_id: id of resource to list statistics for
        :param start_time: Start datetime from which metrics will be used
        :param stop_time: End datetime from which metrics will be used
        :param granularity: frequency of marking metric point, in seconds
        :param aggregation: Should be chosen in accordance with policy
                            aggregations
        :return: value of aggregated metric
        """

        if start_time is not None and not isinstance(start_time, datetime):
            raise exception.InvalidParameter(parameter='start_time',
                                             parameter_type=datetime)

        if stop_time is not None and not isinstance(stop_time, datetime):
            raise exception.InvalidParameter(parameter='stop_time',
                                             parameter_type=datetime)

        raw_kwargs = dict(
            metric=metric,
            start=start_time,
            stop=stop_time,
            resource_id=resource_id,
            granularity=granularity,
            aggregation=aggregation,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        statistics = self.query_retry(
            f=self.gnocchi.metric.get_measures, **kwargs)

        if statistics:
            # return value of latest measure
            # measure has structure [time, granularity, value]
            return statistics[-1][2]
