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

"""Test fixture wiring the Cinder API emulator via wsgi-intercept.

Sets up in-process WSGI interception for the Cinder API emulator and
patches ``clients.get_sdk_connection()`` so that ``CinderHelper`` gets
an openstacksdk ``Connection`` with ``block_storage.endpoint_override``
pointing at the in-process Cinder API emulator.

Usage in tests::

    from watcher.tests.functional import topology


    class MyTest(WatcherFunctionalTestCase):
        STORAGE_TOPOLOGY = topology.StorageTopology(
            storage_nodes=[topology.StorageNode(host='storage-1@backend1')],
            pools=[
                topology.Pool(
                    name='storage-1@backend1#pool1', total_capacity_gb=1000
                )
            ],
        )

This fixture composes with ``NovaPlacementFixture``: when both are
active, pass the other fixture's ``endpoint_overrides`` so the combined
``Connection`` carries compute, placement, *and* block-storage
endpoint overrides together (a single patched
``clients.get_sdk_connection`` serves every helper).
"""

import fixtures

from keystoneauth1 import noauth
from keystoneauth1 import session as ks_session
from openstack import connection as os_connection
from oslo_utils.fixture import uuidsentinel
from wsgi_intercept import interceptor

from watcher.common.service import Singleton
from watcher.decision_engine.model.collector import cinder as cinder_coll
from watcher.tests.local_fixtures import cinder_api_emulator


class CinderFixture(fixtures.Fixture):
    """Wire the Cinder API emulator into the test environment.

    Installs wsgi-intercept for the Cinder emulator and patches
    ``clients.get_sdk_connection`` so that ``CinderHelper`` gets a
    real openstacksdk ``Connection`` connected to the emulated
    endpoint.

    :param topology: A ``StorageTopology`` instance.
    :param model_path: Path to an XML or JSON model file.
    :param endpoint_overrides: Extra openstacksdk ``Connection``
        endpoint-override kwargs (e.g. from another emulator fixture)
        merged into the same ``Connection`` so a single patch of
        ``clients.get_sdk_connection`` serves every helper.
    """

    def __init__(
        self, topology=None, model_path=None, endpoint_overrides=None
    ):
        super().__init__()
        self._topology = topology
        self._model_path = model_path
        self._endpoint_overrides = dict(endpoint_overrides or {})
        self.cinder_emulator = None
        self.cinder_url = None

    @property
    def endpoint_overrides(self):
        """Overrides this fixture contributes (after setUp)."""
        return {'block_storage_endpoint_override': self.cinder_url}

    def setUp(self):
        super().setUp()

        # Create emulator

        self.cinder_emulator = cinder_api_emulator.CinderAPIEmulator()

        if self._model_path:
            self.cinder_emulator.load_model(self._model_path)
        elif self._topology is not None:
            self.cinder_emulator.load_topology(self._topology)

        # Install wsgi-intercept

        cinder_host = str(uuidsentinel.cinder_api_host)
        self.cinder_url = 'http://%s:80' % cinder_host

        cinder_intercept = interceptor.RequestsInterceptor(
            lambda: self.cinder_emulator.app, url=self.cinder_url + '/'
        )
        cinder_intercept.install_intercept()
        self.addCleanup(cinder_intercept.uninstall_intercept)

        # Build a single sdk Connection carrying every active
        # emulator's endpoint override, so NovaHelper/CinderHelper
        # both keep working regardless of which was built last.
        overrides = dict(self._endpoint_overrides)
        overrides.update(self.endpoint_overrides)

        auth = noauth.NoAuth(endpoint=self.cinder_url)
        sess = ks_session.Session(auth=auth)
        sdk_conn = os_connection.Connection(session=sess, **overrides)

        self.useFixture(
            fixtures.MockPatch(
                'watcher.common.clients.get_sdk_connection',
                return_value=sdk_conn,
            )
        )

        # Ensure the storage collector can discover block-storage.
        self.useFixture(
            fixtures.MockPatch(
                'watcher.common.keystone_helper'
                '.KeystoneHelper.is_service_enabled_by_type',
                return_value=True,
            )
        )

    def reload_topology(self, topology):
        """Reload topology on the emulator (for mid-test changes).

        Also invalidates the collector's cached storage data model so
        the next audit rebuilds it from the updated emulator state.
        """
        self.cinder_emulator.load_topology(topology)
        self._invalidate_collector_model()

    @staticmethod
    def _invalidate_collector_model():
        """Reset the Cinder collector singleton's cached model."""
        collector = Singleton._instances.get(
            cinder_coll.CinderClusterDataModelCollector
        )
        if collector is not None:
            collector._cluster_data_model = None
