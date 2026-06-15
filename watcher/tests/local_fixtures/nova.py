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

"""Test fixture wiring Nova and Placement API emulators via wsgi-intercept.

Sets up in-process WSGI interception for both Nova and Placement APIs,
and patches ``clients.get_sdk_connection()`` so that NovaHelper gets
an openstacksdk Connection routed to the intercepted Nova and Placement
endpoints.

Usage in tests::

    from watcher.tests.functional import topology


    class MyTest(WatcherFunctionalTestCase):
        COMPUTE_TOPOLOGY = topology.ComputeTopology(
            compute_nodes=[
                topology.ComputeNode(uuid='n1', hostname='compute-1'),
                topology.ComputeNode(uuid='n2', hostname='compute-2'),
            ],
            instances=[
                topology.Instance(
                    uuid='i1', name='vm-1', host='compute-1', vcpus=2
                )
            ],
        )

The fixture can also load topology from XML or JSON files
(format is auto-detected by extension)::

    NovaPlacementFixture(model_path='path/to/model.xml')
    NovaPlacementFixture(model_path='path/to/topology.json')
"""

import fixtures

from keystoneauth1 import noauth
from keystoneauth1 import session as ks_session
from openstack import connection as os_connection
from oslo_utils.fixture import uuidsentinel
from wsgi_intercept import interceptor

from watcher.common.service import Singleton
from watcher.decision_engine.model.collector import nova as nova_coll
from watcher.tests.local_fixtures import nova_api_emulator
from watcher.tests.local_fixtures import placement_api_emulator


class NovaPlacementFixture(fixtures.Fixture):
    """Wire Nova and Placement API emulators into the test environment.

    Installs wsgi-intercept for both emulators and patches:

    - ``clients.get_sdk_connection()`` so that ``NovaHelper`` gets an
      openstacksdk ``Connection`` with ``compute.endpoint_override``
      and ``placement.endpoint_override`` pointing at the in-process
      Nova and Placement API emulators.
    - ``OpenStackClients._cinder`` on every instance so that
      ``NovaHelper.__init__`` does not fail trying to authenticate.

    The topology (compute nodes, instances, aggregates) can be
    supplied as a ``ComputeTopology`` object, or loaded from
    XML / JSON model files.

    :param topology: A ``ComputeTopology`` instance.
    :param model_path: Path to a model file (XML or JSON).
    """

    def __init__(self, topology=None, model_path=None):
        super().__init__()
        self._topology = topology
        self._model_path = model_path
        self.nova_emulator = None
        self.placement_emulator = None
        self.nova_url = None
        self.placement_url = None

    def setUp(self):
        super().setUp()

        # Create emulators

        self.nova_emulator = nova_api_emulator.NovaAPIEmulator()
        self.placement_emulator = placement_api_emulator.PlacementAPIEmulator()

        if self._model_path:
            self.nova_emulator.load_model(self._model_path)
            self.placement_emulator.load_model(self._model_path)

        if self._topology is not None:
            self.nova_emulator.load_topology(self._topology)
            self.placement_emulator.load_topology(self._topology)
        elif not self._model_path:
            self.placement_emulator.load_topology()

        # Install wsgi-intercept

        nova_host = str(uuidsentinel.nova_api_host)
        placement_host = str(uuidsentinel.placement_api_host)

        self.nova_url = 'http://%s:80' % nova_host
        self.placement_url = 'http://%s:80' % placement_host

        nova_intercept = interceptor.RequestsInterceptor(
            lambda: self.nova_emulator.app, url=self.nova_url + '/'
        )
        nova_intercept.install_intercept()
        self.addCleanup(nova_intercept.uninstall_intercept)

        placement_intercept = interceptor.RequestsInterceptor(
            lambda: self.placement_emulator.app, url=self.placement_url + '/'
        )
        placement_intercept.install_intercept()
        self.addCleanup(placement_intercept.uninstall_intercept)

        # Build clients

        nova_endpoint = self.nova_url + '/v2.1'
        placement_endpoint = self.placement_url

        auth = noauth.NoAuth(endpoint=nova_endpoint)
        sess = ks_session.Session(auth=auth)

        # Nova/compute: openstacksdk Connection (used by NovaHelper)
        # Placement: openstacksdk proxy (used by PlacementHelper)
        # Endpoint overrides must be set via the constructor so
        # they are available during service version discovery.
        sdk_conn = os_connection.Connection(
            session=sess,
            compute_endpoint_override=nova_endpoint,
            placement_endpoint_override=placement_endpoint,
        )

        # Patch get_sdk_connection to return our pre-configured
        # Connection with compute.endpoint_override set.
        self.useFixture(
            fixtures.MockPatch(
                'watcher.common.clients.get_sdk_connection',
                return_value=sdk_conn,
            )
        )

    def reload_topology(self, topology):
        """Reload topology on both emulators (for mid-test changes).

        Also invalidates the collector's cached cluster data model so
        the next audit rebuilds it from the updated emulator state.
        """
        self.nova_emulator.load_topology(topology)
        self.placement_emulator.load_topology(topology)
        self._invalidate_collector_model()

    @staticmethod
    def _invalidate_collector_model():
        """Reset the collector singleton's cached model.

        The NovaClusterDataModelCollector is a singleton that caches
        its cluster data model after the first build. After reloading
        the emulator topology, the cached model is stale. Setting it
        to None forces a full rebuild on the next access.
        """
        collector = Singleton._instances.get(
            nova_coll.NovaClusterDataModelCollector
        )
        if collector is not None:
            collector._cluster_data_model = None
