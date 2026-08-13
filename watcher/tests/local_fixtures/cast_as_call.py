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


class CastAsCallFixture(fixtures.Fixture):
    """Make RPC casts behave as calls for synchronous testing.

    Replaces oslo_messaging.RPCClient.cast with RPCClient.call so that
    fire-and-forget casts become synchronous. This makes functional tests
    deterministic by ensuring the remote method completes before the test
    continues.
    """

    def setUp(self):
        super().setUp()
        self.useFixture(
            fixtures.MonkeyPatch(
                'oslo_messaging.RPCClient.cast', messaging.RPCClient.call
            )
        )
