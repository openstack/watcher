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

import abc
import time

from oslo_config import cfg
from oslo_log import log

from watcher.common import exception

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class DataSourceBase(object):
    """Base Class for datasources in Watcher

    This base class defines the abstract methods that datasources should
    implement and contains details on the values expected for parameters as
    well as what the values for return types should be.
    """

    """Possible options for the parameters named aggregate"""
    AGGREGATES = ['mean', 'min', 'max', 'count']

    """Possible options for the parameters named resource_type"""
    RESOURCE_TYPES = ['compute_node', 'instance', 'bare_metal', 'storage']

    """Each datasource should have a uniquely identifying name"""
    NAME = ''

    """Possible metrics a datasource can support and their internal name"""
    METRIC_MAP = dict(host_cpu_usage=None,
                      host_ram_usage=None,
                      host_outlet_temp=None,
                      host_inlet_temp=None,
                      host_airflow=None,
                      host_power=None,
                      instance_cpu_usage=None,
                      instance_ram_usage=None,
                      instance_ram_allocated=None,
                      instance_l3_cache_usage=None,
                      instance_root_disk_size=None,
                      )

    def _get_meter(self, meter_name):
        """Retrieve the meter from the metric map or raise error"""
        meter = self.METRIC_MAP.get(meter_name)
        if meter is None:
            raise exception.MetricNotAvailable(metric=meter_name)
        return meter

    def query_retry(self, f, *args, ignored_exc=None, **kwargs):
        """Attempts to retrieve metrics from the external service

        Attempts to access data from the external service and handles
        exceptions upon exception the retrieval should be retried in accordance
        to the value of query_max_retries
        :param f: The method that performs the actual querying for metrics
        :param args: Array of arguments supplied to the method
        :param ignored_exc: An exception or tuple of exceptions that shouldn't
                            be retried, for example "NotFound" exceptions.
        :param kwargs: The amount of arguments supplied to the method
        :return: The value as retrieved from the external service
        """

        num_retries = CONF.watcher_datasources.query_max_retries
        timeout = CONF.watcher_datasources.query_timeout
        ignored_exc = ignored_exc or tuple()

        for i in range(num_retries):
            try:
                return f(*args, **kwargs)
            except ignored_exc as e:
                LOG.debug("Got an ignored exception (%s) while calling: %s ",
                          e, f)
                return
            except Exception as e:
                LOG.exception(e)
                self.query_retry_reset(e)
                LOG.warning("Retry %d of %d while retrieving metrics retry "
                            "in %d seconds", i+1, num_retries, timeout)
                time.sleep(timeout)

    @abc.abstractmethod
    def query_retry_reset(self, exception_instance):
        """Abstract method to perform reset operations upon request failure"""
        pass

    @abc.abstractmethod
    def list_metrics(self):
        """Returns the supported metrics that the datasource can retrieve

        :return: List of supported metrics containing keys from METRIC_MAP
        """
        pass

    @abc.abstractmethod
    def check_availability(self):
        """Tries to contact the datasource to see if it is available

        :return: True or False with true meaning the datasource is available
        """
        pass

    @abc.abstractmethod
    def statistic_aggregation(self, resource=None, resource_type=None,
                              meter_name=None, period=300, aggregate='mean',
                              granularity=300):
        """Retrieves and converts metrics based on the specified parameters

        :param resource: Resource object as defined in watcher models such as
                         ComputeNode and Instance
        :param resource_type: Indicates which type of object is supplied
                              to the resource parameter
        :param meter_name: The desired metric to retrieve as key from
                           METRIC_MAP
        :param period: Time span to collect metrics from in seconds
        :param granularity: Interval between samples in measurements in
                            seconds
        :param aggregate: Aggregation method to extract value from set of
                          samples
        :return: The gathered value for the metric the type of value depends on
                 the meter_name
        """

        pass

    @abc.abstractmethod
    def statistic_series(self, resource=None, resource_type=None,
                         meter_name=None, start_time=None, end_time=None,
                         granularity=300):
        """Retrieves metrics based on the specified parameters over a period

        :param resource: Resource object as defined in watcher models such as
                         ComputeNode and Instance
        :param resource_type: Indicates which type of object is supplied
                              to the resource parameter
        :param meter_name: The desired metric to retrieve as key from
                           METRIC_MAP
        :param start_time: The datetime to start retrieving metrics for
        :type start_time: datetime.datetime
        :param end_time: The datetime to limit the retrieval of metrics to
        :type end_time: datetime.datetime
        :param granularity: Interval between samples in measurements in
                            seconds
        :return: Dictionary of key value pairs with timestamps and metric
                 values
        """

        pass

    @abc.abstractmethod
    def get_host_cpu_usage(self, resource, period, aggregate,
                           granularity=None):
        """Get the cpu usage for a host such as a compute_node

        :return: cpu usage as float ranging between 0 and 100 representing the
                 total cpu usage as percentage
        """
        pass

    @abc.abstractmethod
    def get_host_ram_usage(self, resource, period, aggregate,
                           granularity=None):
        """Get the ram usage for a host such as a compute_node

        :return: ram usage as float in kibibytes
        """
        pass

    @abc.abstractmethod
    def get_host_outlet_temp(self, resource, period, aggregate,
                             granularity=None):
        """Get the outlet temperature for a host such as compute_node

        :return: outlet temperature as float in degrees celsius
        """
        pass

    @abc.abstractmethod
    def get_host_inlet_temp(self, resource, period, aggregate,
                            granularity=None):
        """Get the inlet temperature for a host such as compute_node

        :return: inlet temperature as float in degrees celsius
        """
        pass

    @abc.abstractmethod
    def get_host_airflow(self, resource, period, aggregate,
                         granularity=None):
        """Get the airflow for a host such as compute_node

        :return: airflow as float in cfm
        """
        pass

    @abc.abstractmethod
    def get_host_power(self, resource, period, aggregate,
                       granularity=None):
        """Get the power for a host such as compute_node

        :return: power as float in watts
        """
        pass

    @abc.abstractmethod
    def get_instance_cpu_usage(self, resource, period,
                               aggregate, granularity=None):
        """Get the cpu usage for an instance

        :return: cpu usage as float ranging between 0 and 100 representing the
                 total cpu usage as percentage
        """
        pass

    @abc.abstractmethod
    def get_instance_ram_usage(self, resource, period,
                               aggregate, granularity=None):
        """Get the ram usage for an instance

        :return: ram usage as float in megabytes
        """
        pass

    @abc.abstractmethod
    def get_instance_ram_allocated(self, resource, period,
                                   aggregate, granularity=None):
        """Get the ram allocated for an instance

        :return: total ram allocated as float in megabytes
        """
        pass

    @abc.abstractmethod
    def get_instance_l3_cache_usage(self, resource, period,
                                    aggregate, granularity=None):
        """Get the l3 cache usage for an instance

        :return: l3 cache usage as integer in bytes
        """
        pass

    @abc.abstractmethod
    def get_instance_root_disk_size(self, resource, period,
                                    aggregate, granularity=None):
        """Get the size of the root disk for an instance

        :return: root disk size as float in gigabytes
        """
        pass
