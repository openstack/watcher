# -*- encoding: utf-8 -*-
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


class StopInstance(base.BaseAction):
    """Stops a server instance

    This action will allow you to stop a server instance on a compute host.
    This is typically used when migration is not available or desired.

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

    def stop_instance(self):
        nova = nova_helper.NovaHelper(osc=self.osc)
        LOG.debug("Stopping instance %s", self.instance_uuid)

        instance = nova.find_instance(self.instance_uuid)
        if not instance:
            raise exception.InstanceNotFound(name=self.instance_uuid)

        try:
            result = nova.stop_instance(instance_id=self.instance_uuid)
            if result:
                LOG.info(_("Successfully stopped instance %(uuid)s"),
                         {'uuid': self.instance_uuid})
            else:
                LOG.error("Failed to stop instance %(uuid)s",
                          {'uuid': self.instance_uuid})
            return result
        except Exception as exc:
            LOG.exception(exc)
            LOG.critical("Unexpected error occurred while stopping "
                         "instance %(uuid)s: %(error)s",
                         {'uuid': self.instance_uuid,
                          'error': str(exc)})
            raise

    def execute(self):
        return self.stop_instance()

    def revert_stop_instance(self):
        """Revert the stop action by trying to start the instance"""
        nova = nova_helper.NovaHelper(osc=self.osc)
        LOG.debug("Starting instance %s", self.instance_uuid)

        try:
            # Use start_instance from nova_helper - this method exists
            result = nova.start_instance(instance_id=self.instance_uuid)
            if result:
                LOG.info(_("Successfully reverted stop action and started instance %(uuid)s"),
                         {'uuid': self.instance_uuid})
            else:
                LOG.error("Failed to start instance %(uuid)s",
                          {'uuid': self.instance_uuid})
            return result
        except Exception as exc:
            LOG.exception(exc)
            LOG.critical("Unexpected error occurred while starting "
                         "instance %(uuid)s: %(error)s",
                         {'uuid': self.instance_uuid,
                          'error': str(exc)})
            raise

    def revert(self):
        LOG.debug("Reverting stop action for instance %s", self.instance_uuid)
        return self.revert_stop_instance()

    def abort(self):
        """Abort the stop action - not applicable for stop operations"""
        LOG.warning("Abort operation is not applicable for stop action on "
                    "instance %s", self.instance_uuid)
        return False

    def pre_condition(self):
        # Check for instance existence and its state
        nova = nova_helper.NovaHelper(osc=self.osc)
        try:
            instance = nova.find_instance(self.instance_uuid)
            if not instance:
                raise exception.InstanceNotFound(name=self.instance_uuid)

            # Check instance current state
            current_state = getattr(instance, 'OS-EXT-STS:vm_state')

            # If already stopped, that's fine
            if current_state == 'stopped':
                return True

            LOG.debug("Instance %s pre-condition check: state=%s",
                      self.instance_uuid, current_state)

        except exception.InstanceNotFound:
            raise
        except Exception as exc:
            LOG.exception(exc)
            LOG.error("Pre-condition check failed for instance %s: %s",
                      self.instance_uuid, str(exc))
            raise

    def post_condition(self):
        # Verify the instance is actually stopped
        nova = nova_helper.NovaHelper(osc=self.osc)
        try:
            instance = nova.find_instance(self.instance_uuid)
            if not instance:
                LOG.warning("Instance %s not found during post-condition check",
                            self.instance_uuid)
                return

            current_state = getattr(instance, 'OS-EXT-STS:vm_state')
            LOG.debug("Instance %s post-condition check: state=%s",
                      self.instance_uuid, current_state)

            if current_state != 'stopped':
                if not nova.wait_for_instance_state(instance, 'stopped', 8, 10):
                    LOG.warning("Instance %s may not be fully stopped (state: %s)",
                                self.instance_uuid, current_state)

        except Exception as exc:
            LOG.exception(exc)
            LOG.warning("Post-condition check failed for instance %s: %s",
                        self.instance_uuid, str(exc))

    def get_description(self):
        """Description of the action"""
        return "Stop a VM instance"

