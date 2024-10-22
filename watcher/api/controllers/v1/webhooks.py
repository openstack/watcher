# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Webhook endpoint for Watcher v1 REST API.
"""

from http import HTTPStatus
from oslo_log import log
import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher.api.controllers.v1 import types
from watcher.api.controllers.v1 import utils
from watcher.common import exception
from watcher.decision_engine import rpcapi
from watcher import objects

LOG = log.getLogger(__name__)


class WebhookController(rest.RestController):
    """REST controller for webhooks resource."""

    def __init__(self):
        super(WebhookController, self).__init__()
        self.dc_client = rpcapi.DecisionEngineAPI()

    @wsme_pecan.wsexpose(None, wtypes.text, body=types.jsontype,
                         status_code=HTTPStatus.ACCEPTED)
    def post(self, audit_ident, body):
        """Trigger the given audit.

        :param audit_ident: UUID or name of an audit.
        """

        LOG.debug("Webhook trigger Audit: %s.", audit_ident)

        context = pecan.request.context
        audit = utils.get_resource('Audit', audit_ident)
        if audit is None:
            raise exception.AuditNotFound(audit=audit_ident)
        if audit.audit_type != objects.audit.AuditType.EVENT.value:
            raise exception.AuditTypeNotAllowed(audit_type=audit.audit_type)
        allowed_state = (
            objects.audit.State.PENDING,
            objects.audit.State.SUCCEEDED,
            )
        if audit.state not in allowed_state:
            raise exception.AuditStateNotAllowed(state=audit.state)

        # trigger decision-engine to run the audit
        self.dc_client.trigger_audit(context, audit.uuid)
