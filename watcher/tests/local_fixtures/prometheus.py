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

"""Test fixture wiring the Prometheus API emulator via wsgi-intercept.

Sets up in-process WSGI interception for the Prometheus API so that
watcher's ``PrometheusHelper`` datasource queries are served from
in-memory metric data.

The ``PrometheusAPIClient`` from ``python-observabilityclient``
uses ``requests.Session`` directly, so wsgi-intercept transparently
redirects its HTTP calls to the in-process emulator.

Usage in tests::

    class MyTest(WatcherFunctionalTestCase):
        COMPUTE_TOPOLOGY = (
            topology.ComputeTopology()
            .add_computes(count=2)
            .add_instances(computes=['compute-1'], count=2)
            .update_compute(
                'compute-1', metrics={'cpu': 80.0, 'ram': 16384000.0}
            )
            .update_instance('vm-1', metrics={'cpu': 45.0, 'ram': 2048.0})
        )
        USE_PROMETHEUS = True

Configuration overrides (datasource selection, retry settings) are
NOT set here — they belong in ``WatcherEnvironment`` where
``self.flags()`` provides proper cleanup.
"""

import fixtures

from oslo_utils.fixture import uuidsentinel
from wsgi_intercept import interceptor

from watcher.tests.local_fixtures import prometheus_api_emulator


class PrometheusFixture(fixtures.Fixture):
    """Wire the Prometheus API emulator into the test environment.

    Installs wsgi-intercept for the Prometheus emulator.  The emulator
    starts empty; call ``load_from_topology()`` or ``load_metrics()``
    to populate it with metric data.

    :param hosts: List of host metric dicts (fqdn, uuid, cpu, ram).
    :param instances: List of instance metric dicts (uuid, cpu, ram).
    """

    def __init__(self, hosts=None, instances=None):
        super().__init__()
        self._hosts = hosts
        self._instances = instances
        self.prometheus_emulator = None
        self.prometheus_url = None

    def setUp(self):
        super().setUp()

        self.prometheus_emulator = (
            prometheus_api_emulator.PrometheusAPIEmulator()
        )

        if self._hosts is not None or self._instances is not None:
            self.prometheus_emulator.load_metrics(
                hosts=self._hosts, instances=self._instances
            )

        prometheus_host = str(uuidsentinel.prometheus_api_host)
        self.prometheus_url = 'http://%s:80' % prometheus_host

        prom_intercept = interceptor.RequestsInterceptor(
            lambda: self.prometheus_emulator.app, url=self.prometheus_url + '/'
        )
        prom_intercept.install_intercept()
        self.addCleanup(prom_intercept.uninstall_intercept)

    def load_from_topology(self, topology, fqdn_suffix='.example.com'):
        """Derive and load Prometheus metrics from a ComputeTopology."""
        self.prometheus_emulator.load_from_topology(
            topology, fqdn_suffix=fqdn_suffix
        )

    def reload_metrics(self, hosts=None, instances=None):
        """Reload metrics on the emulator (for mid-test changes)."""
        self.prometheus_emulator.reload_metrics(
            hosts=hosts, instances=instances
        )
