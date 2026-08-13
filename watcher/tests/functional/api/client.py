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

import requests

from oslo_serialization import jsonutils


class WatcherTestClient:
    """Simple HTTP client for Watcher functional tests.

    Sends the authentication headers expected by the Pecan ContextHook
    (X-User-Id, X-Project-Id, X-Auth-Token, X-Roles) so that a real
    RequestContext is created without Keystone.
    """

    def __init__(
        self,
        base_url,
        user_id='bbbbbbbb-1111-2222-3333-444444444444',
        project_id='aaaaaaaa-1111-2222-3333-444444444444',
        roles=None,
    ):
        self.base_url = base_url
        self.user_id = user_id
        self.project_id = project_id
        self.roles = roles or ['admin']

    def _headers(self):
        return {
            'X-Auth-Token': 'fake-token',
            'X-User-Id': self.user_id,
            'X-Project-Id': self.project_id,
            'X-Roles': ','.join(self.roles),
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def get(self, url, **kwargs):
        return requests.get(
            self.base_url + url, headers=self._headers(), **kwargs
        )

    def post(self, url, body, **kwargs):
        return requests.post(
            self.base_url + url,
            data=jsonutils.dumps(body),
            headers=self._headers(),
            **kwargs,
        )

    def patch(self, url, body, **kwargs):
        return requests.patch(
            self.base_url + url,
            data=jsonutils.dumps(body),
            headers=self._headers(),
            **kwargs,
        )

    def delete(self, url, **kwargs):
        return requests.delete(
            self.base_url + url, headers=self._headers(), **kwargs
        )
