# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Minimal Prometheus API emulator for functional tests.

Serves a subset of the Prometheus HTTP API backed by in-memory
metric data.  Metrics can be loaded from:

  - ``ComputeTopology`` objects (``metrics['cpu']``/``metrics['ram']``
    on nodes/instances)
  - Python dicts passed directly from test code
  - JSON files

The emulator can run:

  - In-process via wsgi-intercept (for functional tests)
  - Standalone via dev server (for manual testing / debugging)

Supported endpoints (those used by watcher's PrometheusBase):

    GET  /api/v1/query              (instant vector queries)
    GET  /api/v1/targets            (active scrape targets)
    GET  /api/v1/status/runtimeinfo (health check)
    GET  /-/healthy                 (readiness probe)
    GET  /                          (summary)

Recognised PromQL patterns (regex-matched, not parsed):

    node_cpu_seconds_total{...fqdn='HOST'...}   -> host CPU usage (0-100%)
    node_memory_MemAvailable_bytes{fqdn='HOST'} -> host RAM usage (KiB)
    node_memory_MemTotal_bytes{fqdn='HOST'}     -> host RAM total (KiB)
    ceilometer_cpu{resource='UUID'}             -> instance CPU usage (0-100%)
    ceilometer_memory_usage{resource='UUID'}    -> instance RAM usage (MiB)
"""

import re
import time

from oslo_serialization import jsonutils
from pecan import expose
from pecan import request

from watcher.tests.functional import topology as topo_mod
from watcher.tests.local_fixtures import base_emulator


RESOURCE_RE = re.compile(r"resource='([0-9a-f-]{36})'")
FQDN_RE = re.compile(r"fqdn='([^']+)'")


class _StatusController:
    @expose('json')
    def runtimeinfo(self):
        return {
            'status': 'success',
            'data': {
                'startTime': '2025-01-01T00:00:00Z',
                'CWD': '/prometheus',
                'goroutineCount': 42,
                'GOMAXPROCS': 4,
                'GOGC': '',
                'GODEBUG': '',
                'storageRetention': '15d',
            },
        }


class _V1Controller:
    def __init__(self, emulator):
        self._emulator = emulator
        self.status = _StatusController()

    @expose('json')
    def query(self):
        query = request.params.get('query', '')
        kind, key = self._emulator._identify_query(query)

        if kind == 'instance_ram':
            inst = self._emulator.instances.get(key)
            if inst is None:
                return _prom_empty()
            return _prom_response(inst['ram'], {'resource': key})

        if kind == 'instance_cpu':
            inst = self._emulator.instances.get(key)
            if inst is None:
                return _prom_empty()
            return _prom_response(inst['cpu'], {'resource': key})

        if kind == 'host_cpu':
            host = self._emulator.hosts.get(key)
            if host is None:
                return _prom_empty()
            return _prom_response(host['cpu'], {'fqdn': key})

        if kind == 'host_ram':
            host = self._emulator.hosts.get(key)
            if host is None:
                return _prom_empty()
            return _prom_response(host['ram'], {'fqdn': key})

        return _prom_empty()

    @expose('json')
    def targets(self):
        active = []
        for fqdn in sorted(self._emulator.hosts):
            active.append(
                {
                    'discoveredLabels': {
                        '__address__': '%s:9100' % fqdn,
                        '__metrics_path__': '/metrics',
                        '__scheme__': 'http',
                    },
                    'labels': {
                        'fqdn': fqdn,
                        'instance': '%s:9100' % fqdn,
                        'job': 'node',
                    },
                    'scrapePool': 'node',
                    'scrapeUrl': 'http://%s:9100/metrics' % fqdn,
                    'globalUrl': 'http://%s:9100/metrics' % fqdn,
                    'lastError': '',
                    'lastScrape': '2025-08-27T09:49:58Z',
                    'lastScrapeDuration': 0.05,
                    'health': 'up',
                    'scrapeInterval': '30s',
                    'scrapeTimeout': '10s',
                }
            )
        return {
            'status': 'success',
            'data': {'activeTargets': active, 'droppedTargets': []},
        }


class _DashController:
    @expose()
    def healthy(self):
        return 'Prometheus is Healthy.\n'


class _ApiController:
    def __init__(self, emulator):
        self.v1 = _V1Controller(emulator)


class _PrometheusRootController:
    def __init__(self, emulator):
        self._emulator = emulator
        self.api = _ApiController(emulator)

    @expose()
    def _lookup(self, segment, *remainder):
        if segment == '-':
            return _DashController(), remainder

    @expose('json')
    def index(self):
        return {
            'status': 'success',
            'data': {
                'hosts': len(self._emulator.hosts),
                'instances': len(self._emulator.instances),
            },
        }


def _prom_response(value, labels=None):
    return {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': [
                {'metric': labels or {}, 'value': [time.time(), str(value)]}
            ],
        },
    }


def _prom_empty():
    return {
        'status': 'success',
        'data': {'resultType': 'vector', 'result': []},
    }


class PrometheusAPIEmulator(base_emulator.BaseAPIEmulator):
    """In-memory Prometheus API emulator.

    Manages metric state for hosts and instances and exposes a Pecan
    WSGI app that responds to the PromQL queries watcher generates.

    Metrics can be loaded from ``ComputeTopology`` objects (using the
    ``metrics['cpu']`` and ``metrics['ram']`` entries on nodes and
    instances), from plain dicts, or from JSON files.

    Topology ``metrics['cpu']`` is a normalised fraction (0-1);
    ``metrics['ram']`` is in MiB.  ``load_from_topology()`` converts
    them to raw Prometheus units:

    - CPU: ``cpu * 100`` → 0-100 %
    - Host RAM: ``ram * 1024`` → KiB
    - Instance RAM: ``ram`` → MiB (stored directly)

    Example (in tests)::

        from watcher.tests.functional import topology

        emulator = PrometheusAPIEmulator()
        topo = (
            topology.ComputeTopology()
            .add_computes(count=2)
            .add_instances(computes=['compute-1'], count=2)
            .update_compute('compute-1', metrics={'cpu': 0.80, 'ram': 16384})
            .update_instance('vm-1', metrics={'cpu': 0.45, 'ram': 2048})
        )
        emulator.load_from_topology(topo)
        wsgi_app = emulator.app
    """

    def _init_stores(self):
        self.hosts = {}
        self.instances = {}

    def _make_root_controller(self):
        return _PrometheusRootController(self)

    def load_metrics(self, hosts=None, instances=None):
        """Load metric data from Python dicts in raw Prometheus units.

        Unlike ``load_from_topology()``, values are NOT converted —
        they are stored as-is and returned directly to the strategy.

        :param hosts: list of dicts with keys ``fqdn``, ``uuid``,
            ``cpu`` (float, 0-100 %), ``ram`` (float, KiB).
        :param instances: list of dicts with keys ``uuid``,
            ``cpu`` (float, 0-100 %), ``ram`` (float, MiB).
        """
        for host_def in hosts or []:
            fqdn = host_def['fqdn']
            self.hosts[fqdn] = {
                'cpu': float(host_def.get('cpu', 0.0)),
                'ram': float(host_def.get('ram', 0.0)),
                'uuid': host_def.get('uuid', ''),
            }

        for inst_def in instances or []:
            uid = inst_def['uuid']
            self.instances[uid] = {
                'cpu': float(inst_def.get('cpu', 0.0)),
                'ram': float(inst_def.get('ram', 0.0)),
            }

    def reload_metrics(self, hosts=None, instances=None):
        """Clear state and reload metrics."""
        self.reset()
        self.load_metrics(hosts=hosts, instances=instances)

    def load_from_topology(self, topology, fqdn_suffix='.example.com'):
        """Derive Prometheus metrics from a ComputeTopology object.

        Uses the ``metrics['cpu']`` and ``metrics['ram']`` entries
        from ``ComputeNode`` and ``Instance`` dataclasses and converts
        them to raw Prometheus units:

        - CPU: ``cpu * 100`` (percentage; cpu is a 0-1 fraction)
        - Host RAM: ``ram * 1024`` (KiB; ram is in MiB)
        - Instance RAM: ``ram`` (MiB; stored directly)

        Host FQDNs are constructed as ``hostname + fqdn_suffix``.

        :param topology: A ``ComputeTopology`` instance.
        :param fqdn_suffix: Suffix appended to hostnames to form FQDNs.
        """
        self.reset()
        compute_nodes = topo_mod.normalize(topology.compute_nodes)
        instances = topo_mod.normalize(topology.instances)

        for node_def in compute_nodes or []:
            hostname = node_def['hostname']
            fqdn = hostname + fqdn_suffix
            metrics = node_def.get('metrics', {})
            self.hosts[fqdn] = {
                'cpu': float(metrics.get('cpu', 0.0)) * 100,
                'ram': float(metrics.get('ram', 0.0)) * 1024,
                'uuid': node_def.get('uuid', ''),
            }

        for inst_def in instances or []:
            metrics = inst_def.get('metrics', {})
            self.instances[inst_def['uuid']] = {
                'cpu': float(metrics.get('cpu', 0.0)) * 100,
                'ram': float(metrics.get('ram', 0.0)),
            }

    def load_from_json(self, json_path):
        """Load metrics from a JSON file.

        Expected format::

            {
                "hosts": [
                    {
                        "fqdn": "compute-1.example.com",
                        "uuid": "...",
                        "cpu": 80.0,
                        "ram": 25000.0,
                    }
                ],
                "instances": [{"uuid": "...", "cpu": 45.0, "ram": 2048.0}],
            }
        """
        with open(json_path, 'rb') as f:
            data = jsonutils.load(f)
        self.load_metrics(
            hosts=data.get('hosts'), instances=data.get('instances')
        )

    def _identify_query(self, query):
        """Identify the metric kind and lookup key from a PromQL query."""
        if 'ceilometer_memory_usage' in query:
            m = RESOURCE_RE.search(query)
            if m:
                return 'instance_ram', m.group(1)

        if 'ceilometer_cpu' in query:
            m = RESOURCE_RE.search(query)
            if m:
                return 'instance_cpu', m.group(1)

        if 'node_cpu_seconds_total' in query:
            m = FQDN_RE.search(query)
            if m:
                return 'host_cpu', m.group(1)

        if (
            'node_memory_MemTotal_bytes' in query
            or 'node_memory_MemAvailable_bytes' in query
        ):
            m = FQDN_RE.search(query)
            if m:
                return 'host_ram', m.group(1)

        return None, None


def create_app(model_path=None):
    """Factory to create a configured emulator."""
    return base_emulator.create_app(
        PrometheusAPIEmulator, model_path=model_path
    )


def main():
    base_emulator.run_standalone(
        PrometheusAPIEmulator, 'Prometheus API emulator', 9090
    )


if __name__ == '__main__':
    main()
