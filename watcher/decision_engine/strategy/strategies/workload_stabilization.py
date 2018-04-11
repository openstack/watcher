# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica LLC
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
#

import copy
import itertools
import math
import random
import re

import oslo_cache
from oslo_config import cfg
from oslo_log import log
import oslo_utils

from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.model import element
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)
CONF = cfg.CONF


def _set_memoize(conf):
    oslo_cache.configure(conf)
    region = oslo_cache.create_region()
    configured_region = oslo_cache.configure_cache_region(conf, region)
    return oslo_cache.core.get_memoization_decorator(conf,
                                                     configured_region,
                                                     'cache')


class WorkloadStabilization(base.WorkloadStabilizationBaseStrategy):
    """Workload Stabilization control using live migration

    This is workload stabilization strategy based on standard deviation
    algorithm. The goal is to determine if there is an overload in a cluster
    and respond to it by migrating VMs to stabilize the cluster.

    This strategy has been tested in a small (32 nodes) cluster.

    It assumes that live migrations are possible in your cluster.
    """

    MIGRATION = "migrate"
    MEMOIZE = _set_memoize(CONF)

    DATASOURCE_METRICS = ['host_cpu_usage', 'instance_cpu_usage',
                          'instance_ram_usage', 'host_memory_usage']

    def __init__(self, config, osc=None):
        """Workload Stabilization control using live migration

        :param config: A mapping containing the configuration of this strategy
        :type config: :py:class:`~.Struct` instance
        :param osc: :py:class:`~.OpenStackClients` instance
        """
        super(WorkloadStabilization, self).__init__(config, osc)
        self.weights = None
        self.metrics = None
        self.thresholds = None
        self.host_choice = None
        self.instance_metrics = None
        self.retry_count = None
        self.periods = None
        self.aggregation_method = None

    @classmethod
    def get_name(cls):
        return "workload_stabilization"

    @classmethod
    def get_display_name(cls):
        return _("Workload stabilization")

    @classmethod
    def get_translatable_display_name(cls):
        return "Workload stabilization"

    @property
    def granularity(self):
        return self.input_parameters.get('granularity', 300)

    @classmethod
    def get_schema(cls):
        return {
            "properties": {
                "metrics": {
                    "description": "Metrics used as rates of cluster loads.",
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["cpu_util", "memory.resident"]
                    },
                    "default": ["cpu_util"]
                },
                "thresholds": {
                    "description": "Dict where key is a metric and value "
                                   "is a trigger value.",
                    "type": "object",
                    "properties": {
                        "cpu_util": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "memory.resident": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        }
                    },
                    "default": {"cpu_util": 0.1, "memory.resident": 0.1}
                },
                "weights": {
                    "description": "These weights used to calculate "
                                   "common standard deviation. Name of weight"
                                   " contains meter name and _weight suffix.",
                    "type": "object",
                    "properties": {
                        "cpu_util_weight": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "memory.resident_weight": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        }
                    },
                    "default": {"cpu_util_weight": 1.0,
                                "memory.resident_weight": 1.0}
                },
                "instance_metrics": {
                    "description": "Mapping to get hardware statistics using"
                                   " instance metrics",
                    "type": "object",
                    "default": {"cpu_util": "compute.node.cpu.percent",
                                "memory.resident": "hardware.memory.used"}
                },
                "host_choice": {
                    "description": "Method of host's choice. There are cycle,"
                                   " retry and fullsearch methods. "
                                   "Cycle will iterate hosts in cycle. "
                                   "Retry will get some hosts random "
                                   "(count defined in retry_count option). "
                                   "Fullsearch will return each host "
                                   "from list.",
                    "type": "string",
                    "default": "retry"
                },
                "retry_count": {
                    "description": "Count of random returned hosts",
                    "type": "number",
                    "minimum": 1,
                    "default": 1
                },
                "periods": {
                    "description": "These periods are used to get statistic "
                                   "aggregation for instance and host "
                                   "metrics. The period is simply a repeating"
                                   " interval of time into which the samples"
                                   " are grouped for aggregation. Watcher "
                                   "uses only the last period of all received"
                                   " ones.",
                    "type": "object",
                    "properties": {
                        "instance": {
                            "type": "integer",
                            "minimum": 0
                        },
                        "node": {
                            "type": "integer",
                            "minimum": 0
                        },
                    },
                    "default": {"instance": 720, "node": 600}
                },
                "aggregation_method": {
                    "description": "Function used to aggregate multiple "
                                   "measures into an aggregate. For example, "
                                   "the min aggregation method will aggregate "
                                   "the values of different measures to the "
                                   "minimum value of all the measures in the "
                                   "time range.",
                    "type": "object",
                    "properties": {
                        "instance": {
                            "type": "string",
                            "default": 'mean'
                        },
                        "node": {
                            "type": "string",
                            "default": 'mean'
                        },
                    },
                    "default": {"instance": 'mean', "node": 'mean'}
                },
                "granularity": {
                    "description": "The time between two measures in an "
                                   "aggregated timeseries of a metric.",
                    "type": "number",
                    "minimum": 0,
                    "default": 300
                },
            }
        }

    @classmethod
    def get_config_opts(cls):
        return [
            cfg.ListOpt(
                "datasources",
                help="Datasources to use in order to query the needed metrics."
                     " If one of strategy metric isn't available in the first"
                     " datasource, the next datasource will be chosen.",
                item_type=cfg.types.String(choices=['gnocchi', 'ceilometer',
                                                    'monasca']),
                default=['gnocchi', 'ceilometer', 'monasca'])
        ]

    def transform_instance_cpu(self, instance_load, host_vcpus):
        """Transform instance cpu utilization to overall host cpu utilization.

        :param instance_load: dict that contains instance uuid and
            utilization info.
        :param host_vcpus: int
        :return: float value
        """
        return (instance_load['cpu_util'] *
                (instance_load['vcpus'] / float(host_vcpus)))

    @MEMOIZE
    def get_instance_load(self, instance):
        """Gathering instance load through ceilometer/gnocchi statistic.

        :param instance: instance for which statistic is gathered.
        :return: dict
        """
        LOG.debug('get_instance_load started')
        instance_load = {'uuid': instance.uuid, 'vcpus': instance.vcpus}
        for meter in self.metrics:
            avg_meter = self.datasource_backend.statistic_aggregation(
                instance.uuid, meter, self.periods['instance'],
                self.granularity,
                aggregation=self.aggregation_method['instance'])
            if avg_meter is None:
                LOG.warning(
                    "No values returned by %(resource_id)s "
                    "for %(metric_name)s", dict(
                        resource_id=instance.uuid, metric_name=meter))
                return
            if meter == 'cpu_util':
                avg_meter /= float(100)
            instance_load[meter] = avg_meter
        return instance_load

    def normalize_hosts_load(self, hosts):
        normalized_hosts = copy.deepcopy(hosts)
        for host in normalized_hosts:
            if 'memory.resident' in normalized_hosts[host]:
                node = self.compute_model.get_node_by_uuid(host)
                normalized_hosts[host]['memory.resident'] /= float(node.memory)

        return normalized_hosts

    def get_available_nodes(self):
        return {node_uuid: node for node_uuid, node in
                self.compute_model.get_all_compute_nodes().items()
                if node.state == element.ServiceState.ONLINE.value and
                node.status == element.ServiceState.ENABLED.value}

    def get_hosts_load(self):
        """Get load of every available host by gathering instances load"""
        hosts_load = {}
        for node_id, node in self.get_available_nodes().items():
            hosts_load[node_id] = {}
            hosts_load[node_id]['vcpus'] = node.vcpus
            for metric in self.metrics:
                resource_id = ''
                avg_meter = None
                meter_name = self.instance_metrics[metric]
                if re.match('^compute.node', meter_name) is not None:
                    resource_id = "%s_%s" % (node.uuid, node.hostname)
                else:
                    resource_id = node_id
                avg_meter = self.datasource_backend.statistic_aggregation(
                    resource_id, self.instance_metrics[metric],
                    self.periods['node'], self.granularity,
                    aggregation=self.aggregation_method['node'])
                if avg_meter is None:
                    LOG.warning('No values returned by node %s for %s',
                                node_id, meter_name)
                    del hosts_load[node_id]
                    break
                else:
                    if meter_name == 'hardware.memory.used':
                        avg_meter /= oslo_utils.units.Ki
                    if meter_name == 'compute.node.cpu.percent':
                        avg_meter /= 100
                hosts_load[node_id][metric] = avg_meter
        return hosts_load

    def get_sd(self, hosts, meter_name):
        """Get standard deviation among hosts by specified meter"""
        mean = 0
        variaton = 0
        for host_id in hosts:
            mean += hosts[host_id][meter_name]
        mean /= len(hosts)
        for host_id in hosts:
            variaton += (hosts[host_id][meter_name] - mean) ** 2
        variaton /= len(hosts)
        sd = math.sqrt(variaton)
        return sd

    def calculate_weighted_sd(self, sd_case):
        """Calculate common standard deviation among meters on host"""
        weighted_sd = 0
        for metric, value in zip(self.metrics, sd_case):
            try:
                weighted_sd += value * float(self.weights[metric + '_weight'])
            except KeyError as exc:
                LOG.exception(exc)
                raise exception.WatcherException(
                    _("Incorrect mapping: could not find associated weight"
                      " for %s in weight dict.") % metric)
        return weighted_sd

    def calculate_migration_case(self, hosts, instance, src_node, dst_node):
        """Calculate migration case

        Return list of standard deviation values, that appearing in case of
        migration of instance from source host to destination host
        :param hosts: hosts with their workload
        :param instance: the virtual machine
        :param src_node: the source node
        :param dst_node: the destination node
        :return: list of standard deviation values
        """
        migration_case = []
        new_hosts = copy.deepcopy(hosts)
        instance_load = self.get_instance_load(instance)
        if not instance_load:
            return
        s_host_vcpus = new_hosts[src_node.uuid]['vcpus']
        d_host_vcpus = new_hosts[dst_node.uuid]['vcpus']
        for metric in self.metrics:
            if metric == 'cpu_util':
                new_hosts[src_node.uuid][metric] -= (
                    self.transform_instance_cpu(instance_load, s_host_vcpus))
                new_hosts[dst_node.uuid][metric] += (
                    self.transform_instance_cpu(instance_load, d_host_vcpus))
            else:
                new_hosts[src_node.uuid][metric] -= instance_load[metric]
                new_hosts[dst_node.uuid][metric] += instance_load[metric]
        normalized_hosts = self.normalize_hosts_load(new_hosts)
        for metric in self.metrics:
            migration_case.append(self.get_sd(normalized_hosts, metric))
        migration_case.append(new_hosts)
        return migration_case

    def get_current_weighted_sd(self, hosts_load):
        """Calculate current weighted sd"""
        current_sd = []
        normalized_load = self.normalize_hosts_load(hosts_load)
        for metric in self.metrics:
            metric_sd = self.get_sd(normalized_load, metric)
            current_sd.append(metric_sd)
        current_sd.append(hosts_load)
        return self.calculate_weighted_sd(current_sd[:-1])

    def simulate_migrations(self, hosts):
        """Make sorted list of pairs instance:dst_host"""
        def yield_nodes(nodes):
            if self.host_choice == 'cycle':
                for i in itertools.cycle(nodes):
                    yield [i]
            if self.host_choice == 'retry':
                while True:
                    yield random.sample(nodes, self.retry_count)
            if self.host_choice == 'fullsearch':
                while True:
                    yield nodes

        instance_host_map = []
        nodes = sorted(list(self.get_available_nodes()))
        current_weighted_sd = self.get_current_weighted_sd(hosts)
        for src_host in nodes:
            src_node = self.compute_model.get_node_by_uuid(src_host)
            c_nodes = copy.copy(nodes)
            c_nodes.remove(src_host)
            node_list = yield_nodes(c_nodes)
            for instance in self.compute_model.get_node_instances(src_node):
                # NOTE: skip exclude instance when migrating
                if instance.watcher_exclude:
                    LOG.debug("Instance is excluded by scope, "
                              "skipped: %s", instance.uuid)
                    continue
                if instance.state not in [element.InstanceState.ACTIVE.value,
                                          element.InstanceState.PAUSED.value]:
                    continue
                min_sd_case = {'value': current_weighted_sd}
                for dst_host in next(node_list):
                    dst_node = self.compute_model.get_node_by_uuid(dst_host)
                    sd_case = self.calculate_migration_case(
                        hosts, instance, src_node, dst_node)
                    if sd_case is None:
                        break

                    weighted_sd = self.calculate_weighted_sd(sd_case[:-1])

                    if weighted_sd < min_sd_case['value']:
                        min_sd_case = {
                            'host': dst_node.uuid, 'value': weighted_sd,
                            's_host': src_node.uuid, 'instance': instance.uuid}
                        instance_host_map.append(min_sd_case)
                if sd_case is None:
                    continue
        return sorted(instance_host_map, key=lambda x: x['value'])

    def check_threshold(self):
        """Check if cluster is needed in balancing"""
        hosts_load = self.get_hosts_load()
        normalized_load = self.normalize_hosts_load(hosts_load)
        for metric in self.metrics:
            metric_sd = self.get_sd(normalized_load, metric)
            LOG.info("Standard deviation for %s is %s.",
                     (metric, metric_sd))
            if metric_sd > float(self.thresholds[metric]):
                LOG.info("Standard deviation of %s exceeds"
                         " appropriate threshold %s.",
                         (metric, metric_sd))
                return self.simulate_migrations(hosts_load)

    def add_migration(self,
                      resource_id,
                      migration_type,
                      source_node,
                      destination_node):
        parameters = {'migration_type': migration_type,
                      'source_node': source_node,
                      'destination_node': destination_node}
        self.solution.add_action(action_type=self.MIGRATION,
                                 resource_id=resource_id,
                                 input_parameters=parameters)

    def create_migration_instance(self, mig_instance, mig_source_node,
                                  mig_destination_node):
        """Create migration VM"""
        if self.compute_model.migrate_instance(
                mig_instance, mig_source_node, mig_destination_node):
            self.add_migration(mig_instance.uuid, 'live',
                               mig_source_node.uuid,
                               mig_destination_node.uuid)

    def migrate(self, instance_uuid, src_host, dst_host):
        mig_instance = self.compute_model.get_instance_by_uuid(instance_uuid)
        mig_source_node = self.compute_model.get_node_by_uuid(
            src_host)
        mig_destination_node = self.compute_model.get_node_by_uuid(
            dst_host)
        self.create_migration_instance(mig_instance, mig_source_node,
                                       mig_destination_node)

    def fill_solution(self):
        self.solution.model = self.compute_model
        return self.solution

    def pre_execute(self):
        LOG.info("Initializing Workload Stabilization")

        if not self.compute_model:
            raise exception.ClusterStateNotDefined()

        if self.compute_model.stale:
            raise exception.ClusterStateStale()

        self.weights = self.input_parameters.weights
        self.metrics = self.input_parameters.metrics
        self.thresholds = self.input_parameters.thresholds
        self.host_choice = self.input_parameters.host_choice
        self.instance_metrics = self.input_parameters.instance_metrics
        self.retry_count = self.input_parameters.retry_count
        self.periods = self.input_parameters.periods
        self.aggregation_method = self.input_parameters.aggregation_method

    def do_execute(self):
        migration = self.check_threshold()
        if migration:
            hosts_load = self.get_hosts_load()
            min_sd = 1
            balanced = False
            for instance_host in migration:
                instance = self.compute_model.get_instance_by_uuid(
                    instance_host['instance'])
                src_node = self.compute_model.get_node_by_uuid(
                    instance_host['s_host'])
                dst_node = self.compute_model.get_node_by_uuid(
                    instance_host['host'])
                if instance.disk > dst_node.disk:
                    continue
                instance_load = self.calculate_migration_case(
                    hosts_load, instance, src_node, dst_node)
                weighted_sd = self.calculate_weighted_sd(instance_load[:-1])
                if weighted_sd < min_sd:
                    min_sd = weighted_sd
                    hosts_load = instance_load[-1]
                    self.migrate(instance_host['instance'],
                                 instance_host['s_host'],
                                 instance_host['host'])

                for metric, value in zip(self.metrics, instance_load[:-1]):
                    if value < float(self.thresholds[metric]):
                        balanced = True
                        break
                if balanced:
                    break

    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        self.fill_solution()

        LOG.debug(self.compute_model.to_string())
