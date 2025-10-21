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
from oslo_utils import timeutils


LOG = log.getLogger(__name__)


@enginefacade.transaction_context_provider
class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, user_id=None, project_id=None, is_admin=None,
                 roles=None, timestamp=None, request_id=None, auth_token=None,
                 overwrite=True, user_name=None, project_name=None,
                 domain_name=None, domain_id=None, auth_token_info=None,
                 **kwargs):
        """Stores several additional request parameters:

        :param domain_id: The ID of the domain.
        :param domain_name: The name of the domain.
        :param is_public_api: Specifies whether the request should be processed
                              without authentication.

        """
        user = kwargs.pop('user', None)
        tenant = kwargs.pop('tenant', None)
        super().__init__(
            auth_token=auth_token,
            user_id=user_id or user,
            project_id=project_id or tenant,
            domain_id=kwargs.pop('domain', None) or domain_name or domain_id,
            user_domain_id=kwargs.pop('user_domain', None),
            project_domain_id=kwargs.pop('project_domain', None),
            is_admin=is_admin,
            read_only=kwargs.pop('read_only', False),
            show_deleted=kwargs.pop('show_deleted', False),
            request_id=request_id,
            resource_uuid=kwargs.pop('resource_uuid', None),
            is_admin_project=kwargs.pop('is_admin_project', True),
            overwrite=overwrite,
            roles=roles,
            global_request_id=kwargs.pop('global_request_id', None),
            system_scope=kwargs.pop('system_scope', None))

        # Note(sean-k-mooney): we should audit what we are using
        # this for and possibly remove it or document it.
        self.auth_token_info = auth_token_info

        if not timestamp:
            timestamp = timeutils.utcnow()
        if isinstance(timestamp, str):
            timestamp = timeutils.parse_isotime(timestamp)
        self.timestamp = timestamp

    def to_dict(self):
        values = super().to_dict()
        values.update({
            'auth_token_info': getattr(self, 'auth_token_info', None),
            'timestamp': self.timestamp.isoformat(),
        })
        return values

    def __str__(self):
        return f"<Context {self.to_dict()}>"


def make_context(*args, **kwargs):
    return RequestContext(*args, **kwargs)
