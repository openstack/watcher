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


class FakeMonascaMetrics(object):
    def __init__(self):
        self.emptytype = ""

    def empty_one_metric(self, emptytype):
        self.emptytype = emptytype

    def mock_get_statistics(self, resource=None, resource_type=None,
                            meter_name=None, period=None, aggregate='mean',
                            granularity=None):
        result = 0.0
        if meter_name == 'host_cpu_usage':
            result = self.get_usage_compute_node_cpu(resource)
        elif meter_name == 'instance_cpu_usage':
            result = self.get_average_usage_instance_cpu(resource)
        return result

    def mock_get_statistics_wb(self, resource=None, resource_type=None,
                               meter_name=None, period=None, aggregate='mean',
                               granularity=None):
        """Statistics for workload balance strategy"""

        result = 0.0
        if meter_name == 'instance_cpu_usage':
            result = self.get_average_usage_instance_cpu_wb(resource)
        return result

    @staticmethod
    def get_usage_compute_node_cpu(*args, **kwargs):
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """

        resource = args[0]
        uuid = resource.uuid

        measurements = {}
        # node 0
        measurements['Node_0'] = 7
        measurements['Node_1'] = 7
        # node 1
        measurements['Node_2'] = 80
        # node 2
        measurements['Node_3'] = 5
        measurements['Node_4'] = 5
        measurements['Node_5'] = 10
        # node 3
        measurements['Node_6'] = 8
        measurements['Node_19'] = 10
        # node 4
        measurements['INSTANCE_7'] = 4

        if uuid not in measurements.keys():
            # measurements[uuid] = random.randint(1, 4)
            measurements[uuid] = 8

        statistics = [
            {'columns': ['avg'],
             'statistics': [[float(measurements[str(uuid)])]]}]
        cpu_usage = None
        for stat in statistics:
            avg_col_idx = stat['columns'].index('avg')
            values = [r[avg_col_idx] for r in stat['statistics']]
            value = float(sum(values)) / len(values)
            cpu_usage = value
        return cpu_usage

    @staticmethod
    def get_average_usage_instance_cpu(*args, **kwargs):
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """

        resource = args[0]
        uuid = resource.uuid

        measurements = {}
        # node 0
        measurements['INSTANCE_0'] = 7
        measurements['INSTANCE_1'] = 7
        # node 1
        measurements['INSTANCE_2'] = 10
        # node 2
        measurements['INSTANCE_3'] = 5
        measurements['INSTANCE_4'] = 5
        measurements['INSTANCE_5'] = 10
        # node 3
        measurements['INSTANCE_6'] = 8
        # node 4
        measurements['INSTANCE_7'] = 4

        if uuid not in measurements.keys():
            # measurements[uuid] = random.randint(1, 4)
            measurements[uuid] = 8

        statistics = [
            {'columns': ['avg'],
             'statistics': [[float(measurements[str(uuid)])]]}]
        cpu_usage = None
        for stat in statistics:
            avg_col_idx = stat['columns'].index('avg')
            values = [r[avg_col_idx] for r in stat['statistics']]
            value = float(sum(values)) / len(values)
            cpu_usage = value
        return cpu_usage
