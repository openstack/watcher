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


class FakeCeilometerMetrics(object):
    NAME = 'ceilometer'

    def __init__(self):
        self.emptytype = ""

    def empty_one_metric(self, emptytype):
        self.emptytype = emptytype

    def mock_get_statistics(self, resource=None, resource_type=None,
                            meter_name=None, period=None, aggregate='mean',
                            granularity=None):
        result = 0
        if meter_name == 'host_cpu_usage':
            result = self.get_usage_compute_node_cpu(resource)
        elif meter_name == 'host_ram_usage':
            result = self.get_usage_compute_node_ram(resource)
        elif meter_name == 'host_outlet_temp':
            result = self.get_average_outlet_temp(resource)
        elif meter_name == 'host_inlet_temp':
            result = self.get_average_inlet_temp(resource)
        elif meter_name == 'host_airflow':
            result = self.get_average_airflow(resource)
        elif meter_name == 'host_power':
            result = self.get_average_power(resource)
        elif meter_name == 'instance_cpu_usage':
            result = self.get_average_usage_instance_cpu(resource)
        elif meter_name == 'instance_ram_usage':
            result = self.get_average_usage_instance_memory(resource)
        return result

    def mock_get_statistics_nn(self, resource=None, meter_name=None,
                               period=None, aggregate='mean', granularity=300):
        """Statistics for noisy neighbor strategy

        Signature should match DataSourceBase.get_instance_l3_cache_usage
        """

        result = 0.0
        if period == 100:
            result = self.get_average_l3_cache_current(resource)
        if period == 200:
            result = self.get_average_l3_cache_previous(resource)
        return result

    def mock_get_statistics_wb(self, resource=None, resource_type=None,
                               meter_name=None, period=None, aggregate='mean',
                               granularity=None):
        """Statistics for workload balance strategy"""

        result = 0.0
        if meter_name == 'instance_cpu_usage':
            result = self.get_average_usage_instance_cpu_wb(resource)
        elif meter_name == 'instance_ram_usage':
            result = self.get_average_usage_instance_memory_wb(resource)
        return result

    @staticmethod
    def get_average_l3_cache_current(resource):
        """The average l3 cache used by instance"""

        uuid = resource.uuid

        mock = {}
        mock['73b09e16-35b7-4922-804e-e8f5d9b740fc'] = 35 * oslo_utils.units.Ki
        mock['cae81432-1631-4d4e-b29c-6f3acdcde906'] = 30 * oslo_utils.units.Ki
        mock['INSTANCE_3'] = 40 * oslo_utils.units.Ki
        mock['INSTANCE_4'] = 35 * oslo_utils.units.Ki

        return mock[str(uuid)]

    @staticmethod
    def get_average_l3_cache_previous(resource):
        """The average l3 cache used by instance"""

        uuid = resource.uuid

        mock = {}
        mock['73b09e16-35b7-4922-804e-e8f5d9b740fc'] = 34.5 * (
            oslo_utils.units.Ki)
        mock['cae81432-1631-4d4e-b29c-6f3acdcde906'] = 30.5 * (
            oslo_utils.units.Ki)
        mock['INSTANCE_3'] = 60 * oslo_utils.units.Ki
        mock['INSTANCE_4'] = 22.5 * oslo_utils.units.Ki

        return mock[str(uuid)]

    @staticmethod
    def get_average_outlet_temp(resource):
        """The average outlet temperature for host"""

        uuid = resource.uuid
        mock = {}
        mock["fa69c544-906b-4a6a-a9c6-c1f7a8078c73"] = 30
        # use a big value to make sure it exceeds threshold
        mock["af69c544-906b-4a6a-a9c6-c1f7a8078c73"] = 100
        if uuid not in mock.keys():
            mock[uuid] = 100
        return float(mock[str(uuid)])

    @staticmethod
    def get_usage_compute_node_ram(resource):

        uuid = resource.uuid
        mock = {}
        # Ceilometer returns hardware.memory.used samples in KB.
        mock['Node_0'] = 7 * oslo_utils.units.Ki
        mock['Node_1'] = 5 * oslo_utils.units.Ki
        mock['Node_2'] = 29 * oslo_utils.units.Ki
        mock['Node_3'] = 8 * oslo_utils.units.Ki
        mock['Node_4'] = 4 * oslo_utils.units.Ki

        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = 8

        return float(mock[str(uuid)])

    @staticmethod
    def get_average_airflow(resource):
        """The average outlet temperature for host"""

        uuid = resource.uuid
        mock = {}
        mock['Node_0'] = 400
        # use a big value to make sure it exceeds threshold
        mock['Node_1'] = 100
        if uuid not in mock.keys():
            mock[uuid] = 200
        return mock[str(uuid)]

    @staticmethod
    def get_average_inlet_temp(resource):
        """The average outlet temperature for host"""

        uuid = resource.uuid
        mock = {}
        mock['Node_0'] = 24
        mock['Node_1'] = 26
        if uuid not in mock.keys():
            mock[uuid] = 28
        return mock[str(uuid)]

    @staticmethod
    def get_average_power(resource):
        """The average outlet temperature for host"""

        uuid = resource.uuid
        mock = {}
        mock['Node_0'] = 260
        mock['Node_1'] = 240
        if uuid not in mock.keys():
            mock[uuid] = 200
        return mock[str(uuid)]

    @staticmethod
    def get_usage_compute_node_cpu(*args, **kwargs):
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """

        resource = args[0]
        uuid = "%s_%s" % (resource.uuid, resource.hostname)

        measurements = {}
        # node 0
        measurements['Node_0_hostname_0'] = 7
        measurements['Node_1_hostname_1'] = 7
        measurements['fa69c544-906b-4a6a-a9c6-c1f7a8078c73_hostname_0'] = 7
        measurements['af69c544-906b-4a6a-a9c6-c1f7a8078c73_hostname_1'] = 7
        # node 1
        measurements['Node_2_hostname_2'] = 80
        # node 2
        measurements['Node_3_hostname_3'] = 5
        measurements['Node_4_hostname_4'] = 5
        measurements['Node_5_hostname_5'] = 10

        # node 3
        measurements['Node_6_hostname_6'] = 8
        # This node doesn't send metrics
        measurements['LOST_NODE_hostname_7'] = None
        measurements['Node_19_hostname_19'] = 10
        # node 4
        measurements['INSTANCE_7_hostname_7'] = 4

        result = measurements[uuid]
        return float(result) if result is not None else None

    @staticmethod
    def get_average_usage_instance_cpu_wb(resource):
        """The last VM CPU usage values to average

        :param resource:
        :return:
        """

        uuid = resource.uuid

        mock = {}
        # node 0
        mock['INSTANCE_1'] = 80
        mock['73b09e16-35b7-4922-804e-e8f5d9b740fc'] = 50
        # node 1
        mock['INSTANCE_3'] = 20
        mock['INSTANCE_4'] = 10

        return float(mock[str(uuid)])

    @staticmethod
    def get_average_usage_instance_memory_wb(resource):
        uuid = resource.uuid

        mock = {}
        # node 0
        mock['INSTANCE_1'] = 30
        mock['73b09e16-35b7-4922-804e-e8f5d9b740fc'] = 12
        # node 1
        mock['INSTANCE_3'] = 12
        mock['INSTANCE_4'] = 12

        return mock[str(uuid)]

    @staticmethod
    def get_average_usage_instance_cpu(*args, **kwargs):
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """

        resource = args[0]
        uuid = resource.uuid

        mock = {}
        # node 0
        mock['INSTANCE_0'] = 7
        mock['INSTANCE_1'] = 7
        # node 1
        mock['INSTANCE_2'] = 10
        # node 2
        mock['INSTANCE_3'] = 5
        mock['INSTANCE_4'] = 5
        mock['INSTANCE_5'] = 10
        # node 3
        mock['INSTANCE_6'] = 8
        # node 4
        mock['INSTANCE_7'] = 4
        mock['LOST_INSTANCE'] = None

        # metrics might be missing in scenarios which do not do computations
        if uuid not in mock.keys():
            mock[uuid] = 0

        return mock[str(uuid)]

    @staticmethod
    def get_average_usage_instance_memory(resource):
        uuid = resource.uuid

        mock = {}
        # node 0
        mock['INSTANCE_0'] = 2
        mock['INSTANCE_1'] = 5
        # node 1
        mock['INSTANCE_2'] = 5
        # node 2
        mock['INSTANCE_3'] = 8
        mock['INSTANCE_4'] = 5
        mock['INSTANCE_5'] = 16
        # node 3
        mock['INSTANCE_6'] = 8
        # node 4
        mock['INSTANCE_7'] = 4

        return mock[str(uuid)]

    @staticmethod
    def get_average_usage_instance_disk(resource):
        uuid = resource.uuid

        mock = {}
        # node 0
        mock['INSTANCE_0'] = 2
        mock['INSTANCE_1'] = 2
        # node 1
        mock['INSTANCE_2'] = 2
        # node 2
        mock['INSTANCE_3'] = 10
        mock['INSTANCE_4'] = 15
        mock['INSTANCE_5'] = 20
        # node 3
        mock['INSTANCE_6'] = 8
        # node 4
        mock['INSTANCE_7'] = 4

        return mock[str(uuid)]
