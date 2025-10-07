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
from watcher.applier.actions import base
from watcher.common import nova_helper

LOG = log.getLogger(__name__)


class Stop(base.BaseAction):
    """Stops a server instance

    This action will allow you to stop a server instance on a compute host.

    The action schema is::

        schema = Schema({
         'resource_id': str,  # should be a UUID
        })

    The `resource_id` is the UUID of the server instance to stop.
    The action will check if the instance exists, verify its current state,
    and then proceed to stop it if it is in a state that allows stopping.
    """

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'resource_id': {
                    'type': 'string',
                    "minlength": 1,
                    "pattern": ("^([a-fA-F0-9]){8}-([a-fA-F0-9]){4}-"
                                "([a-fA-F0-9]){4}-([a-fA-F0-9]){4}-"
                                "([a-fA-F0-9]){12}$")
                },
            },
            'required': ['resource_id'],
            'additionalProperties': False,
        }

    @property
    def instance_uuid(self):
        return self.resource_id

    def stop(self):
        nova = nova_helper.NovaHelper(osc=self.osc)
        LOG.debug("Stopping instance %s", self.instance_uuid)

        try:
            result = nova.stop_instance(instance_id=self.instance_uuid)
        except nova_helper.nvexceptions.ClientException as e:
            LOG.debug("Nova client exception occurred while stopping "
                      "instance %(instance)s. Exception: %(exception)s",
                      {'instance': self.instance_uuid, 'exception': e})
            return False
        except Exception as e:
            LOG.debug("An unexpected error occurred while stopping "
                      "instance %s: %s", self.instance_uuid, str(e))
            return False

        if result:
            LOG.debug(
                "Successfully stopped instance %(uuid)s",
                {'uuid': self.instance_uuid}
            )
            return True
        else:
            # Check if failure was due to instance not found (idempotent)
            instance = nova.find_instance(self.instance_uuid)
            if not instance:
                LOG.info(
                    "Instance %(uuid)s not found, "
                    "considering stop operation successful",
                    {'uuid': self.instance_uuid}
                )
                return True
            else:
                LOG.error(
                    "Failed to stop instance %(uuid)s",
                    {'uuid': self.instance_uuid}
                )
                return False

    def execute(self):
        return self.stop()

    def _revert_stop(self):
        """Revert the stop action by trying to start the instance"""
        nova = nova_helper.NovaHelper(osc=self.osc)
        LOG.debug("Starting instance %s", self.instance_uuid)

        try:
            result = nova.start_instance(instance_id=self.instance_uuid)
            if result:
                LOG.debug(
                    "Successfully reverted stop action and started instance "
                    "%(uuid)s",
                    {'uuid': self.instance_uuid}
                )
                return result
            else:
                LOG.info(
                    "Failed to start instance %(uuid)s during revert. "
                    "This may be normal for instances with special configs.",
                    {'uuid': self.instance_uuid}
                )
        except Exception as exc:
            LOG.info(
                "Could not start instance %(uuid)s during revert: %(error)s. "
                "This may be normal for instances with special configs.",
                {'uuid': self.instance_uuid, 'error': str(exc)}
            )
        return False

    def revert(self):
        LOG.debug("Reverting stop action for instance %s", self.instance_uuid)
        return self._revert_stop()

    def abort(self):
        """Abort the stop action - not applicable for stop operations"""
        LOG.info("Abort operation is not applicable for stop action on "
                 " instance %s", self.instance_uuid)
        return False

    def pre_condition(self):
        # Check for instance existence and its state
        nova = nova_helper.NovaHelper(osc=self.osc)
        try:
            instance = nova.find_instance(self.instance_uuid)
            if not instance:
                LOG.debug(
                    "Instance %(uuid)s not found during pre-condition check. "
                    "Considering this acceptable for stop operation.",
                    {'uuid': self.instance_uuid}
                )
                return

            # Log instance current state
            current_state = instance.status
            LOG.debug("Instance %s pre-condition check: state=%s",
                      self.instance_uuid, current_state)

        except Exception as exc:
            LOG.exception("Pre-condition check failed for instance %s: %s",
                          self.instance_uuid, str(exc))
            raise

    def post_condition(self):
        pass

    def get_description(self):
        """Description of the action"""
        return "Stop a VM instance"
