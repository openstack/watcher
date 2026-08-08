#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from oslo_log import log

from watcher._i18n import _
from watcher.applier.actions import base
from watcher.common import exception
from watcher.common import nova_helper


LOG = log.getLogger(__name__)


class Delete(base.BaseAction):
    """Deletes a server instance

    This action will allow you to delete a server instance, removing it
    and all associated resources.

    The action schema is::

        schema = Schema(
            {
                'resource_id': str  # should be a UUID
            }
        )

    The `resource_id` is the UUID of the server instance to delete.
    """

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'resource_id': {
                    'type': 'string',
                    "minlength": 1,
                    "pattern": (
                        "^([a-fA-F0-9]){8}-([a-fA-F0-9]){4}-"
                        "([a-fA-F0-9]){4}-([a-fA-F0-9]){4}-"
                        "([a-fA-F0-9]){12}$"
                    ),
                }
            },
            'required': ['resource_id'],
            'additionalProperties': False,
        }

    @property
    def instance_uuid(self):
        return self.resource_id

    def delete(self):
        nova = nova_helper.NovaHelper()
        LOG.debug("Deleting instance %s", self.instance_uuid)

        try:
            result = nova.delete_instance(instance_id=self.instance_uuid)
        except exception.NovaClientError as e:
            LOG.error(
                "Nova client exception occurred while deleting "
                "instance %(instance)s. Exception: %(exception)s",
                {'instance': self.instance_uuid, 'exception': e},
            )
            return False
        except Exception as e:
            LOG.error(
                "An unexpected error occurred while deleting instance %s: %s",
                self.instance_uuid,
                str(e),
            )
            return False

        if result:
            LOG.debug(
                "Successfully deleted instance %(uuid)s",
                {'uuid': self.instance_uuid},
            )
            return True
        else:
            LOG.error(
                "Failed to delete instance %(uuid)s",
                {'uuid': self.instance_uuid},
            )
            return False

    def execute(self):
        return self.delete()

    def revert(self):
        """Revert is not possible for delete action.

        Once an instance is deleted, it cannot be restored.
        """
        LOG.warning(
            "Revert of delete action is not possible for instance %s. "
            "The instance has been permanently removed.",
            self.instance_uuid,
        )
        return False

    def abort(self):
        """Abort the delete action - not applicable for delete operations"""
        LOG.info(
            "Abort operation is not applicable for delete action on "
            "instance %s",
            self.instance_uuid,
        )
        return False

    def pre_condition(self):
        """Check delete preconditions

        Skipping conditions:
        - Instance does not exist
        """
        nova = nova_helper.NovaHelper()

        try:
            nova.find_instance(self.instance_uuid)
        except exception.ComputeResourceNotFound:
            raise exception.ActionSkipped(
                _("Instance %s not found") % self.instance_uuid
            )

    def post_condition(self):
        pass

    def get_description(self):
        """Description of the action"""
        return "Delete a VM instance"
