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

from oslo_context import context
from oslo_db.sqlalchemy import enginefacade
from oslo_log import log


LOG = log.getLogger(__name__)


@enginefacade.transaction_context_provider
class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, is_admin=None, auth_token_info=None, **kwargs):
        super().__init__(is_admin=is_admin, **kwargs)

        # Note(sean-k-mooney): we should audit what we are using
        # this for and possibly remove it or document it.
        self.auth_token_info = auth_token_info

    def to_dict(self):
        values = super().to_dict()
        values.update({'auth_token_info': self.auth_token_info})
        return values

    def __str__(self):
        return f"<Context {self.to_dict()}>"


def make_context(*args, **kwargs):
    return RequestContext(*args, **kwargs)
