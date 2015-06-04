# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

import random
from watcher.decision_engine.api.collector.metrics_resource_collector import \
    MetricsResourceCollector


class FakerMetricsCollector(MetricsResourceCollector):
    def __init__(self):
        pass

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
        mock['VM_0'] = 7
        mock['VM_1'] = 7
        # node 1
        mock['VM_2'] = 10
        # node 2
        mock['VM_3'] = 5
        mock['VM_4'] = 5
        mock['VM_5'] = 10

        # node 3
        mock['VM_6'] = 8

        # node 4
        mock['VM_7'] = 4
        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = 8

        return mock[str(uuid)]

    def get_average_usage_vm_memory(self, uuid):
        mock = {}
        # node 0
        mock['VM_0'] = 2
        mock['VM_1'] = 5
        # node 1
        mock['VM_2'] = 5
        # node 2
        mock['VM_3'] = 8
        mock['VM_4'] = 5
        mock['VM_5'] = 16

        # node 3
        mock['VM_6'] = 8

        # node 4
        mock['VM_7'] = 4
        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = 10

        return mock[str(uuid)]

    def get_average_usage_vm_disk(self, uuid):
        mock = {}
        # node 0
        mock['VM_0'] = 2
        mock['VM_1'] = 2
        # node 1
        mock['VM_2'] = 2
        # node 2
        mock['VM_3'] = 10
        mock['VM_4'] = 15
        mock['VM_5'] = 20

        # node 3
        mock['VM_6'] = 8

        # node 4
        mock['VM_7'] = 4

        if uuid not in mock.keys():
            # mock[uuid] = random.randint(1, 4)
            mock[uuid] = 4

        return mock[str(uuid)]

    def get_virtual_machine_capacity(self, vm_uuid):
        return random.randint(1, 4)

    def get_average_network_incomming(self, node):
        pass

    def get_average_network_outcomming(self, node):
        pass
