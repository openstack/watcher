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

import random

from watcher.metrics_engine.api.metrics_resource_collector import Measure
from watcher.metrics_engine.api.metrics_resource_collector import \
    MetricsResourceCollector


class FakerMetricsCollector(MetricsResourceCollector):
    def __init__(self):
        self.emptytype = ""

    def empty_one_metric(self, emptytype):
        self.emptytype = emptytype

    def get_measurement(self,
                        metric,
                        callback=None,
                        start_time=None,
                        end_time=None,
                        filters=None,
                        aggregation_function=None,
                        intervals=None):

        results = []
        if metric == "compute_cpu_user_percent_gauge":
            if self.emptytype == "CPU_COMPUTE":
                pass
            else:
                results.append(Measure(0, 5))
        elif metric == "instance_cpu_percent_gauge":
            results.append(
                self.get_average_usage_vm_cpu(filters[0].split('=')[1]))
        elif metric == "instance_memory_resident_used_bytes_gauge":
            results.append(
                self.get_average_usage_vm_memory(filters[0].split('=')[1]))
        elif metric == "instance_disk_used_bytes_gauge":
            if self.emptytype == "DISK_COMPUTE":
                pass
            else:
                results.append(
                    self.get_average_usage_vm_disk(filters[0].split('=')[1]))
        elif metric == "compute_memory_used_bytes_gauge":
            if self.emptytype == "MEM_COMPUTE":
                pass
            else:
                results.append(self.get_usage_node_cpu(
                    filters[0].split('=')[1]))
        elif metric == "compute_disk_size_used_bytes_gauge":
            if self.emptytype == "DISK_COMPUTE":
                pass
            else:
                results.append(self.get_usage_node_disk(
                    filters[0].split('=')[1]))
        else:
            results.append(Measure(0, 0))
        return results

    def get_usage_node_disk(self, uuid):
        """The last VM CPU usage values to average

            :param uuid:00
            :return:
            """
        # query influxdb stream

        # compute in stream

        # Normalize
        mock = {}
        # node 0
        mock['Node_0'] = Measure(0, 7)
        mock['Node_1'] = Measure(0, 100)
        # node 1
        mock['Node_2'] = Measure(0, 10)
        # node 2
        mock['Node_3'] = Measure(0, 5)
        mock['Node_4'] = Measure(0, 5)
        mock['Node_5'] = Measure(0, 10)

        # node 3
        mock['Node_6'] = Measure(0, 8)

        # node 4
        mock['VM_7'] = Measure(0, 4)
        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = Measure(0, 8)

        return mock[str(uuid)]

    def get_usage_node_cpu(self, uuid):
        """The last VM CPU usage values to average

            :param uuid:00
            :return:
            """
        # query influxdb stream

        # compute in stream

        # Normalize
        mock = {}
        # node 0
        mock['Node_0'] = Measure(0, 7)
        mock['Node_1'] = Measure(0, 7)
        # node 1
        mock['Node_2'] = Measure(0, 80)
        # node 2
        mock['Node_3'] = Measure(0, 5)
        mock['Node_4'] = Measure(0, 5)
        mock['Node_5'] = Measure(0, 10)

        # node 3
        mock['Node_6'] = Measure(0, 8)

        # node 4
        mock['VM_7'] = Measure(0, 4)
        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = Measure(0, 8)

        return mock[str(uuid)]

    def get_average_usage_vm_cpu(self, uuid):
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """
        # query influxdb stream

        # compute in stream

        # Normalize
        mock = {}
        # node 0
        mock['VM_0'] = Measure(0, 7)
        mock['VM_1'] = Measure(0, 7)
        # node 1
        mock['VM_2'] = Measure(0, 10)
        # node 2
        mock['VM_3'] = Measure(0, 5)
        mock['VM_4'] = Measure(0, 5)
        mock['VM_5'] = Measure(0, 10)

        # node 3
        mock['VM_6'] = Measure(0, 8)

        # node 4
        mock['VM_7'] = Measure(0, 4)
        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = Measure(0, 8)

        return mock[str(uuid)]

    def get_average_usage_vm_memory(self, uuid):
        mock = {}
        # node 0
        mock['VM_0'] = Measure(0, 2)
        mock['VM_1'] = Measure(0, 5)
        # node 1
        mock['VM_2'] = Measure(0, 5)
        # node 2
        mock['VM_3'] = Measure(0, 8)
        mock['VM_4'] = Measure(0, 5)
        mock['VM_5'] = Measure(0, 16)

        # node 3
        mock['VM_6'] = Measure(0, 8)

        # node 4
        mock['VM_7'] = Measure(0, 4)
        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = Measure(0, 10)

        return mock[str(uuid)]

    def get_average_usage_vm_disk(self, uuid):
        mock = {}
        # node 0
        mock['VM_0'] = Measure(0, 2)
        mock['VM_1'] = Measure(0, 2)
        # node 1
        mock['VM_2'] = Measure(0, 2)
        # node 2
        mock['VM_3'] = Measure(0, 10)
        mock['VM_4'] = Measure(0, 15)
        mock['VM_5'] = Measure(0, 20)

        # node 3
        mock['VM_6'] = Measure(0, 8)

        # node 4
        mock['VM_7'] = Measure(0, 4)

        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = Measure(0, 4)

        return mock[str(uuid)]

    def get_virtual_machine_capacity(self, vm_uuid):
        return random.randint(1, 4)

    def get_average_network_incomming(self, node):
        pass

    def get_average_network_outcomming(self, node):
        pass
