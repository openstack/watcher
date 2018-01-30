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

import oslo_utils


class FakeMonascaMetrics(object):
    def __init__(self):
        self.emptytype = ""

    def empty_one_metric(self, emptytype):
        self.emptytype = emptytype

    def mock_get_statistics(self, resource_id=None, meter_name=None,
                            period=None, granularity=None, dimensions=None,
                            aggregation='avg', group_by='*'):
        resource_id = dimensions.get(
            "resource_id") or dimensions.get("hostname")
        result = 0.0
        if meter_name == "cpu.percent":
            result = self.get_usage_node_cpu(resource_id)
        elif meter_name == "vm.cpu.utilization_perc":
            result = self.get_average_usage_instance_cpu(resource_id)
        # elif meter_name == "hardware.memory.used":
        #     result = self.get_usage_node_ram(resource_id)
        # elif meter_name == "memory.resident":
        #     result = self.get_average_usage_instance_memory(resource_id)
        # elif meter_name == "hardware.ipmi.node.outlet_temperature":
        #     result = self.get_average_outlet_temperature(resource_id)
        # elif meter_name == "hardware.ipmi.node.airflow":
        #     result = self.get_average_airflow(resource_id)
        # elif meter_name == "hardware.ipmi.node.temperature":
        #     result = self.get_average_inlet_t(resource_id)
        # elif meter_name == "hardware.ipmi.node.power":
        #     result = self.get_average_power(resource_id)
        return result

    def mock_get_statistics_wb(self, meter_name, dimensions, period,
                               aggregate='avg'):
        resource_id = dimensions.get(
            "resource_id") or dimensions.get("hostname")
        result = 0.0
        if meter_name == "vm.cpu.utilization_perc":
            result = self.get_average_usage_instance_cpu_wb(resource_id)
        return result

    @staticmethod
    def get_average_outlet_temperature(uuid):
        """The average outlet temperature for host"""
        measurements = {}
        measurements['Node_0'] = 30
        # use a big value to make sure it exceeds threshold
        measurements['Node_1'] = 100
        if uuid not in measurements.keys():
            measurements[uuid] = 100
        return [{'columns': ['avg'],
                 'statistics': [[float(measurements[str(uuid)])]]}]

    @staticmethod
    def get_usage_node_ram(uuid):
        measurements = {}
        # Monasca returns hardware.memory.used samples in KB.
        measurements['Node_0'] = 7 * oslo_utils.units.Ki
        measurements['Node_1'] = 5 * oslo_utils.units.Ki
        measurements['Node_2'] = 29 * oslo_utils.units.Ki
        measurements['Node_3'] = 8 * oslo_utils.units.Ki
        measurements['Node_4'] = 4 * oslo_utils.units.Ki

        if uuid not in measurements.keys():
            # measurements[uuid] = random.randint(1, 4)
            measurements[uuid] = 8

        return float(measurements[str(uuid)])

    @staticmethod
    def get_average_airflow(uuid):
        """The average outlet temperature for host"""
        measurements = {}
        measurements['Node_0'] = 400
        # use a big value to make sure it exceeds threshold
        measurements['Node_1'] = 100
        if uuid not in measurements.keys():
            measurements[uuid] = 200
        return [{'columns': ['avg'],
                 'statistics': [[float(measurements[str(uuid)])]]}]

    @staticmethod
    def get_average_inlet_t(uuid):
        """The average outlet temperature for host"""
        measurements = {}
        measurements['Node_0'] = 24
        measurements['Node_1'] = 26
        if uuid not in measurements.keys():
            measurements[uuid] = 28
        return [{'columns': ['avg'],
                 'statistics': [[float(measurements[str(uuid)])]]}]

    @staticmethod
    def get_average_power(uuid):
        """The average outlet temperature for host"""
        measurements = {}
        measurements['Node_0'] = 260
        measurements['Node_1'] = 240
        if uuid not in measurements.keys():
            measurements[uuid] = 200
        return [{'columns': ['avg'],
                 'statistics': [[float(measurements[str(uuid)])]]}]

    @staticmethod
    def get_usage_node_cpu(*args, **kwargs):
        uuid = args[0]
        if type(uuid) is dict:
            uuid = uuid.get("resource_id") or uuid.get("hostname")
        uuid = uuid.rsplit('_', 2)[0]
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """
        # query influxdb stream

        # compute in stream

        # Normalize
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
        # return float(measurements[str(uuid)])

    @staticmethod
    def get_average_usage_instance_cpu_wb(uuid):
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """
        # query influxdb stream

        # compute in stream

        # Normalize
        measurements = {}
        # node 0
        measurements['INSTANCE_1'] = 80
        measurements['73b09e16-35b7-4922-804e-e8f5d9b740fc'] = 50
        # node 1
        measurements['INSTANCE_3'] = 20
        measurements['INSTANCE_4'] = 10
        return [{'columns': ['avg'],
                 'statistics': [[float(measurements[str(uuid)])]]}]

    @staticmethod
    def get_average_usage_instance_cpu(*args, **kwargs):
        uuid = args[0]
        if type(uuid) is dict:
            uuid = uuid.get("resource_id") or uuid.get("hostname")
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """
        # query influxdb stream

        # compute in stream

        # Normalize
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

    @staticmethod
    def get_average_usage_instance_memory(uuid):
        measurements = {}
        # node 0
        measurements['INSTANCE_0'] = 2
        measurements['INSTANCE_1'] = 5
        # node 1
        measurements['INSTANCE_2'] = 5
        # node 2
        measurements['INSTANCE_3'] = 8
        measurements['INSTANCE_4'] = 5
        measurements['INSTANCE_5'] = 16

        # node 3
        measurements['INSTANCE_6'] = 8

        # node 4
        measurements['INSTANCE_7'] = 4
        if uuid not in measurements.keys():
            # measurements[uuid] = random.randint(1, 4)
            measurements[uuid] = 10

        return [{'columns': ['avg'],
                 'statistics': [[float(measurements[str(uuid)])]]}]

    @staticmethod
    def get_average_usage_instance_disk(uuid):
        measurements = {}
        # node 0
        measurements['INSTANCE_0'] = 2
        measurements['INSTANCE_1'] = 2
        # node 1
        measurements['INSTANCE_2'] = 2
        # node 2
        measurements['INSTANCE_3'] = 10
        measurements['INSTANCE_4'] = 15
        measurements['INSTANCE_5'] = 20

        # node 3
        measurements['INSTANCE_6'] = 8

        # node 4
        measurements['INSTANCE_7'] = 4

        if uuid not in measurements.keys():
            # measurements[uuid] = random.randint(1, 4)
            measurements[uuid] = 4

        return [{'columns': ['avg'],
                 'statistics': [[float(measurements[str(uuid)])]]}]
