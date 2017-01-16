# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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

import datetime

from monascaclient import exc

from watcher.common import clients


class MonascaHelper(object):

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.monasca = self.osc.monasca()

    def query_retry(self, f, *args, **kwargs):
        try:
            return f(*args, **kwargs)
        except exc.HTTPUnauthorized:
            self.osc.reset_clients()
            self.monasca = self.osc.monasca()
            return f(*args, **kwargs)
        except Exception:
            raise

    def _format_time_params(self, start_time, end_time, period):
        """Format time-related params to the correct Monasca format

        :param start_time: Start datetime from which metrics will be used
        :param end_time: End datetime from which metrics will be used
        :param period: interval in seconds (int)
        :return: start ISO time, end ISO time, period
        """

        if not period:
            period = int(datetime.timedelta(hours=3).total_seconds())
        if not start_time:
            start_time = (
                datetime.datetime.utcnow() -
                datetime.timedelta(seconds=period))

        start_timestamp = None if not start_time else start_time.isoformat()
        end_timestamp = None if not end_time else end_time.isoformat()

        return start_timestamp, end_timestamp, period

    def statistics_list(self, meter_name, dimensions, start_time=None,
                        end_time=None, period=None,):
        """List of statistics."""
        start_timestamp, end_timestamp, period = self._format_time_params(
            start_time, end_time, period
        )
        raw_kwargs = dict(
            name=meter_name,
            start_time=start_timestamp,
            end_time=end_timestamp,
            dimensions=dimensions,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        statistics = self.query_retry(
            f=self.monasca.metrics.list_measurements, **kwargs)

        return statistics

    def statistic_aggregation(self,
                              meter_name,
                              dimensions,
                              start_time=None,
                              end_time=None,
                              period=None,
                              aggregate='avg',
                              group_by='*'):
        """Representing a statistic aggregate by operators

        :param meter_name: meter names of which we want the statistics
        :param dimensions: dimensions (dict)
        :param start_time: Start datetime from which metrics will be used
        :param end_time: End datetime from which metrics will be used
        :param period: Sampling `period`: In seconds. If no period is given,
                       only one aggregate statistic is returned. If given, a
                       faceted result will be returned, divided into given
                       periods. Periods with no data are ignored.
        :param aggregate: Should be either 'avg', 'count', 'min' or 'max'
        :return: A list of dict with each dict being a distinct result row
        """
        start_timestamp, end_timestamp, period = self._format_time_params(
            start_time, end_time, period
        )

        raw_kwargs = dict(
            name=meter_name,
            start_time=start_timestamp,
            end_time=end_timestamp,
            dimensions=dimensions,
            period=period,
            statistics=aggregate,
            group_by=group_by,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        statistics = self.query_retry(
            f=self.monasca.metrics.list_statistics, **kwargs)

        return statistics
