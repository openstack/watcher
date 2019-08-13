# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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


class Migrate(base.BaseAction):
    """Migrates a server to a destination nova-compute host

    This action will allow you to migrate a server to another compute
    destination host.
    Migration type 'live' can only be used for migrating active VMs.
    Migration type 'cold' can be used for migrating non-active VMs
    as well active VMs, which will be shut down while migrating.

    The action schema is::

        schema = Schema({
         'resource_id': str,  # should be a UUID
         'migration_type': str,  # choices -> "live", "cold"
         'destination_node': str,
         'source_node': str,
        })

    The `resource_id` is the UUID of the server to migrate.
    The `source_node` and `destination_node` parameters are respectively the
    source and the destination compute hostname (list of available compute
    hosts is returned by this command: ``nova service-list --binary
    nova-compute``).

    .. note::

        Nova API version must be 2.56 or above if `destination_node` parameter
        is given.

    """

    # input parameters constants
    MIGRATION_TYPE = 'migration_type'
    LIVE_MIGRATION = 'live'
    COLD_MIGRATION = 'cold'
    DESTINATION_NODE = 'destination_node'
    SOURCE_NODE = 'source_node'

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'destination_node': {
                    "anyof": [
                        {'type': 'string', "minLength": 1},
                        {'type': 'None'}
                        ]
                },
                'migration_type': {
                    'type': 'string',
                    "enum": ["live", "cold"]
                },
                'resource_id': {
                    'type': 'string',
                    "minlength": 1,
                    "pattern": ("^([a-fA-F0-9]){8}-([a-fA-F0-9]){4}-"
                                "([a-fA-F0-9]){4}-([a-fA-F0-9]){4}-"
                                "([a-fA-F0-9]){12}$")
                },
                'resource_name': {
                    'type': 'string',
                    "minlength": 1
                },
                'source_node': {
                    'type': 'string',
                    "minLength": 1
                    }
            },
            'required': ['migration_type', 'resource_id', 'source_node'],
            'additionalProperties': False,
        }

    @property
    def instance_uuid(self):
        return self.resource_id

    @property
    def migration_type(self):
        return self.input_parameters.get(self.MIGRATION_TYPE)

    @property
    def destination_node(self):
        return self.input_parameters.get(self.DESTINATION_NODE)

    @property
    def source_node(self):
        return self.input_parameters.get(self.SOURCE_NODE)

    def _live_migrate_instance(self, nova, destination):
        result = None
        try:
            result = nova.live_migrate_instance(instance_id=self.instance_uuid,
                                                dest_hostname=destination)
        except nova_helper.nvexceptions.ClientException as e:
            LOG.debug("Nova client exception occurred while live "
                      "migrating instance "
                      "%(instance)s.Exception: %(exception)s",
                      {'instance': self.instance_uuid, 'exception': e})

        except Exception as e:
            LOG.exception(e)
            LOG.critical("Unexpected error occurred. Migration failed for "
                         "instance %s. Leaving instance on previous "
                         "host.", self.instance_uuid)

        return result

    def _cold_migrate_instance(self, nova, destination):
        result = None
        try:
            result = nova.watcher_non_live_migrate_instance(
                instance_id=self.instance_uuid,
                dest_hostname=destination)
        except Exception as exc:
            LOG.exception(exc)
            LOG.critical("Unexpected error occurred. Migration failed for "
                         "instance %s. Leaving instance on previous "
                         "host.", self.instance_uuid)
        return result

    def _abort_cold_migrate(self, nova):
        # TODO(adisky): currently watcher uses its own version of cold migrate
        # implement cold migrate using nova dependent on the blueprint
        # https://blueprints.launchpad.net/nova/+spec/cold-migration-with-target
        # Abort operation for cold migrate is dependent on blueprint
        # https://blueprints.launchpad.net/nova/+spec/abort-cold-migration
        LOG.warning("Abort operation for cold migration is not implemented")

    def _abort_live_migrate(self, nova, source, destination):
        return nova.abort_live_migrate(instance_id=self.instance_uuid,
                                       source=source, destination=destination)

    def migrate(self, destination=None):
        nova = nova_helper.NovaHelper(osc=self.osc)
        if destination is None:
            LOG.debug("Migrating instance %s, destination node will be "
                      "determined by nova-scheduler", self.instance_uuid)
        else:
            LOG.debug("Migrate instance %s to %s", self.instance_uuid,
                      destination)
        instance = nova.find_instance(self.instance_uuid)
        if instance:
            if self.migration_type == self.LIVE_MIGRATION:
                return self._live_migrate_instance(nova, destination)
            elif self.migration_type == self.COLD_MIGRATION:
                return self._cold_migrate_instance(nova, destination)
            else:
                raise exception.Invalid(
                    message=(_("Migration of type '%(migration_type)s' is not "
                               "supported.") %
                             {'migration_type': self.migration_type}))
        else:
            raise exception.InstanceNotFound(name=self.instance_uuid)

    def execute(self):
        return self.migrate(destination=self.destination_node)

    def revert(self):
        LOG.info('Migrate action do not revert!')

    def abort(self):
        nova = nova_helper.NovaHelper(osc=self.osc)
        instance = nova.find_instance(self.instance_uuid)
        if instance:
            if self.migration_type == self.COLD_MIGRATION:
                return self._abort_cold_migrate(nova)
            elif self.migration_type == self.LIVE_MIGRATION:
                return self._abort_live_migrate(
                    nova, source=self.source_node,
                    destination=self.destination_node)
        else:
            raise exception.InstanceNotFound(name=self.instance_uuid)

    def pre_condition(self):
        # TODO(jed): check if the instance exists / check if the instance is on
        # the source_node
        pass

    def post_condition(self):
        # TODO(jed): check extra parameters (network response, etc.)
        pass

    def get_description(self):
        """Description of the action"""
        return "Moving a VM instance from source_node to destination_node"
