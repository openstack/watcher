# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import abc

from observabilityclient import prometheus_client
from oslo_config import cfg
from oslo_log import log

from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.datasources import base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class PrometheusBase(base.DataSourceBase):
    """Base class for Prometheus-based datasources

    This class contains shared functionality for querying Prometheus-like
    metrics sources. Subclasses should implement _setup_prometheus_client
    to provide the appropriate client configuration.
    """

    METRIC_MAP = dict(host_cpu_usage='node_cpu_seconds_total',
                      host_ram_usage='node_memory_MemAvailable_bytes',
                      host_outlet_temp=None,
                      host_inlet_temp=None,
                      host_airflow=None,
                      host_power=None,
                      instance_cpu_usage='ceilometer_cpu',
                      instance_ram_usage='ceilometer_memory_usage',
                      instance_ram_allocated='instance.memory',
                      instance_l3_cache_usage=None,
                      instance_root_disk_size='instance.disk',
                      )
    AGGREGATES_MAP = dict(mean='avg', max='max', min='min', count='avg')

    def __init__(self):
        """Initialise the PrometheusBase

        The prometheus based datasource classes use the PrometheusAPIClient
        provided by python-observabilityclient.
        The prometheus_fqdn_labels contains a list the values contained in
        the fqdn_label in the Prometheus instance. When making queries to
        Prometheus we use the fqdn_label to specify the node for which
         metrics are to be retrieved.
        The fqdn_label comes from watcher_client
        config. The prometheus_fqdn_label allows override of the required label
        in Prometheus scrape configs that specifies each target's fqdn.
        """
        self.prometheus = self._setup_prometheus_client()
        self.prometheus_fqdn_label = self._get_fqdn_label()
        self.prometheus_fqdn_labels = (
            self._build_prometheus_fqdn_labels()
        )
        self.prometheus_host_instance_map = (
            self._build_prometheus_host_instance_map()
        )

    @abc.abstractmethod
    def _setup_prometheus_client(self):
        """Initialize the prometheus client with appropriate configuration

        Subclasses must implement this method to provide their specific
        client configuration (direct connection, keystone auth, etc.)

        :return: PrometheusAPIClient instance
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _get_fqdn_label(self):
        """Get the FQDN label configuration

        :return: String containing the FQDN label name
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _get_instance_uuid_label(self):
        """Get the instance UUID label configuration

        :return: String containing the instance UUID label name
        """
        raise NotImplementedError()

    def _build_prometheus_fqdn_labels(self):
        """Build the list of fqdn_label values to be used in host queries

        Watcher knows nodes by their hostname. In Prometheus however the
        scrape targets (also known as 'instances') are specified by I.P.
        (or hostname) and port number and fqdn is stored in a custom 'fqdn'
        label added to Prometheus scrape_configs. Operators can use a
        different custom label instead by setting the prometheus_fqdn_label
        config option under the prometheus_client section of watcher config.
        The built prometheus_fqdn_labels is created with the full list
        of values of the prometheus_fqdn_label label in Prometheus. This will
        be used to create a map of hostname<-->fqdn and to identify if a target
        exist in prometheus for the compute nodes before sending the query.
        :return a set of values of the fqdn label. For example:
                {'foo.example.com', 'bar.example.com'}
                {'foo', 'bar'}
        """
        prometheus_targets = self.prometheus._get(
            "targets?state=active")['data']['activeTargets']
        # >>> prometheus_targets[0]['labels']
        # {'fqdn': 'marios-env-again.controlplane.domain',
        #  'instance': 'localhost:9100', 'job': 'node'}
        fqdn_instance_labels = set()
        for target in prometheus_targets:
            if target.get('labels', {}).get(self.prometheus_fqdn_label):
                fqdn_instance_labels.add(
                    target['labels'].get(self.prometheus_fqdn_label))

        if not fqdn_instance_labels:
            LOG.error(
                "Could not create fqdn labels list from Prometheus "
                "targets config. Prometheus returned the following: %s",
                prometheus_targets
            )
            return set()
        return fqdn_instance_labels

    def _build_prometheus_host_instance_map(self):
        """Build the hostname<-->instance_label mapping needed for queries

        The prometheus_fqdn_labels has the fully qualified domain name
        for hosts. This will create a duplicate map containing only the host
        name part. Depending on the watcher node.hostname either the
        fqdn_instance_labels or the host_instance_map will be used to resolve
        the correct prometheus fqdn_label for queries. In the event the
        fqdn_instance_labels elements are not valid fqdn (for example it has
        hostnames, not fqdn) the host_instance_map cannot be created and
        an empty dictionary is returned with a warning logged.
        :return a dict mapping hostname to instance label. For example:
                {'foo': 'foo.example.com', 'bar': 'bar.example.com'}
        """
        if not self.prometheus_fqdn_labels:
            LOG.error("Cannot build host_instance_map without "
                      "fqdn_instance_labels")
            return {}
        host_instance_map = {
            host: fqdn for (host, fqdn) in (
                (fqdn.split('.')[0], fqdn)
                for fqdn in self.prometheus_fqdn_labels
                if '.' in fqdn
            )
        }
        if not host_instance_map:
            LOG.warning("Creating empty host instance map. Are the keys "
                        "in prometheus_fqdn_labels valid fqdn?")
            return {}
        return host_instance_map

    def _resolve_prometheus_instance_label(self, node_name):
        """Resolve the prometheus instance label to use in queries

        Given the watcher node.hostname, resolve the prometheus instance
        label for use in queries, first trying the fqdn_instance_labels and
        then the host_instance_map (watcher.node_name can be fqdn or hostname).
        If the name is not resolved after the first attempt, rebuild the fqdn
        and host instance maps and try again. This allows for new hosts added
        after the initialisation of the fqdn_instance_labels.
        :param node_name: the watcher node.hostname
        :return String for the prometheus instance label and None if not found
        """
        def _query_maps(node):
            if node in self.prometheus_fqdn_labels:
                return node
            else:
                return self.prometheus_host_instance_map.get(node, None)

        instance_label = _query_maps(node_name)
        # refresh the fqdn and host instance maps and retry
        if not instance_label:
            self.prometheus_fqdn_labels = (
                self._build_prometheus_fqdn_labels()
            )
            self.prometheus_host_instance_map = (
                self._build_prometheus_host_instance_map()
            )
            instance_label = _query_maps(node_name)

        if not instance_label:
            LOG.error("Cannot query prometheus without instance label. "
                      "Could not resolve %s", node_name)
            return None
        return instance_label

    def _resolve_prometheus_aggregate(self, watcher_aggregate, meter):
        """Resolve the prometheus aggregate using self.AGGREGATES_MAP

        This uses the AGGREGATES_MAP to resolve the correct prometheus
        aggregate to use in queries, from the given watcher aggregate
        """
        if watcher_aggregate == 'count':
            LOG.warning('Prometheus data source does not currently support '
                        ' the count aggregate. Proceeding with mean (avg).')
        promql_aggregate = self.AGGREGATES_MAP.get(watcher_aggregate)
        if not promql_aggregate:
            raise exception.InvalidParameter(
                message=(_("Unknown Watcher aggregate %s. This does not "
                           "resolve to any valid prometheus query aggregate.")
                         % watcher_aggregate)
            )
        return promql_aggregate

    def _build_prometheus_query(self, aggregate, meter, instance_label,
                                period, resource=None):
        """Build and return the prometheus query string with the given args

        This function builds and returns the string query that will be sent
        to the Prometheus server /query endpoint. For host cpu usage we use:

        100 - (avg by (fqdn)(rate(node_cpu_seconds_total{mode='idle',
                                       fqdn='some_host'}[300s])) * 100)

        so using prometheus rate function over the specified period, we average
        per instance (all cpus) idle time and then 'everything else' is cpu
        usage time.

        For host memory usage we use:

        (node_memory_MemTotal_bytes{instance='the_host'} -
        avg_over_time(
            node_memory_MemAvailable_bytes{instance='the_host'}[300s]))
            / 1024

        So we take total and subtract available memory to determine
        how much is in use. We use the prometheus xxx_over_time functions
        avg/max/min depending on the aggregate with the specified time period.

        :param aggregate: one of the values of self.AGGREGATES_MAP
        :param meter: the name of the Prometheus meter to use
        :param instance_label: the Prometheus instance label (scrape target).
        :param period: the period in seconds for which to query
        :param resource: the resource object for which metrics are requested
        :return: a String containing the Prometheus query
        :raises watcher.common.exception.InvalidParameter if params are None
        :raises watcher.common.exception.InvalidParameter if meter is not
                known or currently supported (prometheus meter name).
        """
        query_args = None
        uuid_label_key = self._get_instance_uuid_label()
        if (meter is None or aggregate is None or instance_label is None or
                period is None):
            raise exception.InvalidParameter(
                message=(_(
                    "Cannot build prometheus query without args. "
                    "You provided: meter %(mtr)s, aggregate %(agg)s, "
                    "instance_label %(inst)s, period %(prd)s")
                    % {'mtr': meter, 'agg': aggregate,
                       'inst': instance_label, 'prd': period})
            )

        if meter == 'node_cpu_seconds_total':
            query_args = (
                f"100 - ({aggregate} by ({self.prometheus_fqdn_label})"
                f"(rate({meter}{{mode='idle',"
                f"{self.prometheus_fqdn_label}='{instance_label}'}}"
                f"[{period}s])) "
                "* 100)"
            )
        elif meter == 'node_memory_MemAvailable_bytes':
            # Prometheus metric is in B and we need to return KB
            query_args = (
                f"(node_memory_MemTotal_bytes{{"
                f"{self.prometheus_fqdn_label}='{instance_label}'}} "
                f"- {aggregate}_over_time({meter}{{"
                f"{self.prometheus_fqdn_label}='{instance_label}'}}"
                f"[{period}s])) / 1024"
            )
        elif meter == 'ceilometer_memory_usage':
            query_args = (
                f"{aggregate}_over_time({meter}{{"
                f"{uuid_label_key}='{instance_label}'}}[{period}s])"
            )
        elif meter == 'ceilometer_cpu':
            # We are converting the total cumulative cpu time (ns) to cpu usage
            # percentage so we need to divide between the number of vcpus.
            # As this is a percentage metric, we set a max level of 100. It has
            # been observed in very high usage cases, prometheus reporting
            # values higher that 100 what can lead to unexpected behaviors.
            vcpus = resource.vcpus
            if not vcpus:
                LOG.warning(
                    "instance vcpu count not set for instance %s, assuming 1",
                    instance_label
                )
                vcpus = 1
            query_args = (
                f"clamp_max(({aggregate} by ({uuid_label_key})"
                f"(rate({meter}{{{uuid_label_key}='{instance_label}'}}"
                f"[{period}s]))/10e+8) *(100/{vcpus}), 100)"
            )
        else:
            raise exception.InvalidParameter(
                message=(_("Cannot process prometheus meter %s") % meter)
            )

        return query_args

    def check_availability(self):
        """check if Prometheus server is available for queries

         Performs HTTP get on the prometheus API /status/runtimeinfo endpoint.
         The prometheus_client will raise a PrometheuAPIClientError if the
         call is unsuccessful, which is caught here and a warning logged.
        """
        try:
            self.prometheus._get("status/runtimeinfo")
        except prometheus_client.PrometheusAPIClientError:
            LOG.warning(
                "check_availability raised PrometheusAPIClientError. "
                "Is Prometheus server down?"
            )
            return 'not available'
        return 'available'

    def list_metrics(self):
        """Fetch all prometheus metrics from api/v1/label/__name__/values

        The prometheus_client will raise a PrometheuAPIClientError if the
        call is unsuccessful, which is caught here and a warning logged.
        """
        try:
            response = self.prometheus._get("label/__name__/values")
        except prometheus_client.PrometheusAPIClientError:
            LOG.warning(
                "list_metrics raised PrometheusAPIClientError. Is Prometheus"
                "server down?"
            )
            return set()
        return set(response['data'])

    def statistic_aggregation(self, resource=None, resource_type=None,
                              meter_name=None, period=300, aggregate='mean',
                              granularity=300):

        meter = self._get_meter(meter_name)
        query_args = ''
        instance_label = ''

        # For instance resource type, the datasource expects the uuid of the
        # instance to be assigned to a label in the prometheus metrics, with a
        # specific key value.
        if resource_type == 'compute_node':
            instance_label = self._resolve_prometheus_instance_label(
                resource.hostname)
        elif resource_type == 'instance':
            instance_label = resource.uuid
            # For ram_allocated and root_disk size metrics there are no valid
            # values in the prometheus backend store. We rely in the values
            # provided in the vms inventory.
            if meter == 'instance.memory':
                return float(resource.memory)
            elif meter == 'instance.disk':
                return float(resource.disk)
        else:
            LOG.warning(
                "Prometheus data source does not currently support "
                "resource_type %s", resource_type
            )
            return None

        promql_aggregate = self._resolve_prometheus_aggregate(aggregate, meter)
        query_args = self._build_prometheus_query(
            promql_aggregate, meter, instance_label, period, resource
        )
        if not query_args:
            LOG.error("Cannot proceed without valid prometheus query")
            return None

        result = self.query_retry(
            self.prometheus.query, query_args,
            ignored_exc=prometheus_client.PrometheusAPIClientError,
        )

        return float(result[0].value) if result else None

    def statistic_series(self, resource=None, resource_type=None,
                         meter_name=None, start_time=None, end_time=None,
                         granularity=300):
        raise NotImplementedError(
            _('Prometheus helper currently does not support statistic_series. '
              'This can be considered for future enhancement.'))

    def _invert_max_min_aggregate(self, agg):
        """Invert max and min for node/host metric queries from node-exporter

            because we query for 'idle'/'unused' cpu and memory.
            For Watcher 'max cpu used' we query for prometheus 'min idle time'.
            For Watcher 'max memory used' we retrieve min 'unused'/'available'
            memory from Prometheus. This internal function is used exclusively
            by get_host_cpu_usage and get_host_ram_usage.
            :param agg: the metric collection aggregate
            :return: a String aggregate

        """
        if agg == 'max':
            return 'min'
        elif agg == 'min':
            return 'max'
        return agg

    def get_host_cpu_usage(self, resource, period=300,
                           aggregate="mean", granularity=None):
        """Query prometheus for node_cpu_seconds_total

        This calculates the host cpu usage and returns it as a percentage
        The calculation is made by using the cpu 'idle' time, per
        instance (so all CPUs are included). For example the query looks like
        (100 - (avg by (fqdn)(rate(node_cpu_seconds_total
            {mode='idle',fqdn='compute1.example.com'}[300s])) * 100))
        """
        aggregate = self._invert_max_min_aggregate(aggregate)
        cpu_usage = self.statistic_aggregation(
            resource, 'compute_node',
            'host_cpu_usage', period=period,
            granularity=granularity, aggregate=aggregate)
        return float(cpu_usage) if cpu_usage else None

    def get_host_ram_usage(self, resource, period=300,
                           aggregate="mean", granularity=None):
        aggregate = self._invert_max_min_aggregate(aggregate)
        ram_usage = self.statistic_aggregation(
            resource, 'compute_node',
            'host_ram_usage', period=period,
            granularity=granularity, aggregate=aggregate)
        return float(ram_usage) if ram_usage else None

    def get_instance_ram_usage(self, resource, period=300,
                               aggregate="mean", granularity=None):
        ram_usage = self.statistic_aggregation(
            resource, 'instance',
            'instance_ram_usage', period=period,
            granularity=granularity, aggregate=aggregate)
        return ram_usage

    def get_instance_cpu_usage(self, resource, period=300,
                               aggregate="mean", granularity=None):
        cpu_usage = self.statistic_aggregation(
            resource, 'instance',
            'instance_cpu_usage', period=period,
            granularity=granularity, aggregate=aggregate)
        return cpu_usage

    def get_instance_ram_allocated(self, resource, period=300,
                                   aggregate="mean", granularity=None):
        ram_allocated = self.statistic_aggregation(
            resource, 'instance',
            'instance_ram_allocated', period=period,
            granularity=granularity, aggregate=aggregate)
        return ram_allocated

    def get_instance_root_disk_size(self, resource, period=300,
                                    aggregate="mean", granularity=None):
        root_disk_size = self.statistic_aggregation(
            resource, 'instance',
            'instance_root_disk_size', period=period,
            granularity=granularity, aggregate=aggregate)
        return root_disk_size
