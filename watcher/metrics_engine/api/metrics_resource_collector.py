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
import abc
from enum import Enum
import six


class AggregationFunction(Enum):
    MEAN = 'mean'
    COUNT = 'count'


class Measure(object):
    def __init__(self, time, value):
        self.time = time
        self.value = value

    def __str__(self):
        return str(self.time) + " " + str(self.value)


@six.add_metaclass(abc.ABCMeta)
class MetricsResourceCollector(object):
    @abc.abstractmethod
    def get_measurement(self,
                        metric,
                        callback=None,
                        start_time=None,
                        end_time=None,
                        filters=None,
                        aggregation_function=None,
                        intervals=None):
        """

        :param metric: The full name of a metric in the system.
        Must be the complete name. Case sensitive
        :param callback: Asynchronous Callback Functions to live retrev
        :param start_time:Starting time for the query.
        This may be an absolute or relative time.
        :param end_time: An end time for the query.
        If the end time is not supplied, the current time
         on the TSD will be used.
        :param filters: An optional set of tags for filtering or grouping
        :param aggregation_function: A mathematical function
        :param intervals: An optional interval and function
        to reduce the number of data points returned
        :return:
        """
        raise NotImplementedError("Should have implemented this")
