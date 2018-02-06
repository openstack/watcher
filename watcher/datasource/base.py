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


class DataSourceBase(object):

    METRIC_MAP = dict(
        ceilometer=dict(host_cpu_usage='compute.node.cpu.percent',
                        instance_cpu_usage='cpu_util',
                        instance_l3_cache_usage='cpu_l3_cache',
                        host_outlet_temp=(
                            'hardware.ipmi.node.outlet_temperature'),
                        host_airflow='hardware.ipmi.node.airflow',
                        host_inlet_temp='hardware.ipmi.node.temperature',
                        host_power='hardware.ipmi.node.power',
                        instance_ram_usage='memory.resident',
                        instance_ram_allocated='memory',
                        instance_root_disk_size='disk.root.size',
                        host_memory_usage='hardware.memory.used', ),
        gnocchi=dict(host_cpu_usage='compute.node.cpu.percent',
                     instance_cpu_usage='cpu_util',
                     instance_l3_cache_usage='cpu_l3_cache',
                     host_outlet_temp='hardware.ipmi.node.outlet_temperature',
                     host_airflow='hardware.ipmi.node.airflow',
                     host_inlet_temp='hardware.ipmi.node.temperature',
                     host_power='hardware.ipmi.node.power',
                     instance_ram_usage='memory.resident',
                     instance_ram_allocated='memory',
                     instance_root_disk_size='disk.root.size',
                     host_memory_usage='hardware.memory.used'
                     ),
        monasca=dict(host_cpu_usage='cpu.percent',
                     instance_cpu_usage='vm.cpu.utilization_perc',
                     instance_l3_cache_usage=None,
                     host_outlet_temp=None,
                     host_airflow=None,
                     host_inlet_temp=None,
                     host_power=None,
                     instance_ram_usage=None,
                     instance_ram_allocated=None,
                     instance_root_disk_size=None,
                     host_memory_usage=None
                     ),
    )

    @abc.abstractmethod
    def statistic_aggregation(self, resource_id=None, meter_name=None,
                              period=300, granularity=300, dimensions=None,
                              aggregation='avg', group_by='*'):
        pass

    @abc.abstractmethod
    def list_metrics(self):
        pass

    @abc.abstractmethod
    def check_availability(self):
        pass

    @abc.abstractmethod
    def get_host_cpu_usage(self, resource_id, period, aggregate,
                           granularity=None):
        pass

    @abc.abstractmethod
    def get_instance_cpu_usage(self, resource_id, period, aggregate,
                               granularity=None):
        pass

    @abc.abstractmethod
    def get_host_memory_usage(self, resource_id, period, aggregate,
                              granularity=None):
        pass

    @abc.abstractmethod
    def get_instance_memory_usage(self, resource_id, period, aggregate,
                                  granularity=None):
        pass

    @abc.abstractmethod
    def get_instance_l3_cache_usage(self, resource_id, period, aggregate,
                                    granularity=None):
        pass

    @abc.abstractmethod
    def get_instance_ram_allocated(self, resource_id, period, aggregate,
                                   granularity=None):
        pass

    @abc.abstractmethod
    def get_instance_root_disk_allocated(self, resource_id, period, aggregate,
                                         granularity=None):
        pass

    @abc.abstractmethod
    def get_host_outlet_temperature(self, resource_id, period, aggregate,
                                    granularity=None):
        pass

    @abc.abstractmethod
    def get_host_inlet_temperature(self, resource_id, period, aggregate,
                                   granularity=None):
        pass

    @abc.abstractmethod
    def get_host_airflow(self, resource_id, period, aggregate,
                         granularity=None):
        pass

    @abc.abstractmethod
    def get_host_power(self, resource_id, period, aggregate, granularity=None):
        pass
