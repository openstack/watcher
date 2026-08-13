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

import fixtures
import oslo_messaging as messaging

from oslo_config import cfg
from oslo_messaging import conffixture as messaging_conffixture

from watcher.common import rpc


CONF = cfg.CONF


class RPCFixture(fixtures.Fixture):
    """Set up RPC with fake:// transport for testing.

    Configures oslo.messaging to use the in-memory fake driver,
    initializes the global TRANSPORT and NOTIFIER, and cleans up
    fake exchange state between tests.
    """

    def __init__(self, *exmods):
        super().__init__()
        self.exmods = list(exmods)

    def setUp(self):
        super().setUp()
        self.addCleanup(rpc.cleanup)
        self.messaging_conf = messaging_conffixture.ConfFixture(CONF)
        self.messaging_conf.transport_url = 'fake:/'
        self.useFixture(self.messaging_conf)
        rpc.init(CONF)

        def cleanup_in_flight_rpc_messages():
            messaging._drivers.impl_fake.FakeExchangeManager._exchanges = {}

        self.addCleanup(cleanup_in_flight_rpc_messages)
