# Copyright 2017 NEC Corporation
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

import jsonschema

from oslo_log import log

from cinderclient import client as cinder_client
from watcher._i18n import _
from watcher.applier.actions import base
from watcher.common import cinder_helper
from watcher.common import exception
from watcher.common import keystone_helper
from watcher.common import nova_helper
from watcher.common import utils
from watcher import conf

CONF = conf.CONF
LOG = log.getLogger(__name__)


class VolumeMigrate(base.BaseAction):
    """Migrates a volume to destination node or type

    By using this action, you will be able to migrate cinder volume.
    Migration type 'swap' can only be used for migrating attached volume.
    Migration type 'migrate' can be used for migrating detached volume to
    the pool of same volume type.
    Migration type 'retype' can be used for changing volume type of
    detached volume.

    The action schema is::

        schema = Schema({
            'resource_id': str,  # should be a UUID
            'migration_type': str,  # choices -> "swap", "migrate","retype"
            'destination_node': str,
            'destination_type': str,
        })

    The `resource_id` is the UUID of cinder volume to migrate.
    The `destination_node` is the destination block storage pool name.
    (list of available pools are returned by this command: ``cinder
    get-pools``) which is mandatory for migrating detached volume
    to the one with same volume type.
    The `destination_type` is the destination block storage type name.
    (list of available types are returned by this command: ``cinder
    type-list``) which is mandatory for migrating detached volume or
    swapping attached volume to the one with different volume type.
    """

    MIGRATION_TYPE = 'migration_type'
    SWAP = 'swap'
    RETYPE = 'retype'
    MIGRATE = 'migrate'
    DESTINATION_NODE = "destination_node"
    DESTINATION_TYPE = "destination_type"

    def __init__(self, config, osc=None):
        super(VolumeMigrate, self).__init__(config)
        self.temp_username = utils.random_string(10)
        self.temp_password = utils.random_string(10)
        self.cinder_util = cinder_helper.CinderHelper(osc=self.osc)
        self.nova_util = nova_helper.NovaHelper(osc=self.osc)

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
                'resource_name': {
                    'type': 'string',
                    "minlength": 1
                },
                'migration_type': {
                    'type': 'string',
                    "enum": ["swap", "retype", "migrate"]
                },
                'destination_node': {
                    "anyof": [
                        {'type': 'string', "minLength": 1},
                        {'type': 'None'}
                        ]
                },
                'destination_type': {
                    "anyof": [
                        {'type': 'string', "minLength": 1},
                        {'type': 'None'}
                        ]
                }
            },
            'required': ['resource_id', 'migration_type'],
            'additionalProperties': False,
        }

    def validate_parameters(self):
        jsonschema.validate(self.input_parameters, self.schema)
        return True

    @property
    def volume_id(self):
        return self.input_parameters.get(self.RESOURCE_ID)

    @property
    def migration_type(self):
        return self.input_parameters.get(self.MIGRATION_TYPE)

    @property
    def destination_node(self):
        return self.input_parameters.get(self.DESTINATION_NODE)

    @property
    def destination_type(self):
        return self.input_parameters.get(self.DESTINATION_TYPE)

    def _can_swap(self, volume):
        """Judge volume can be swapped"""

        if not volume.attachments:
            return False
        instance_id = volume.attachments[0]['server_id']
        instance_status = self.nova_util.find_instance(instance_id).status

        if (volume.status == 'in-use' and
                instance_status in ('ACTIVE', 'PAUSED', 'RESIZED')):
            return True

        return False

    def _create_user(self, volume, user):
        """Create user with volume attribute and user information"""
        keystone_util = keystone_helper.KeystoneHelper(osc=self.osc)
        project_id = getattr(volume, 'os-vol-tenant-attr:tenant_id')
        user['project'] = project_id
        user['domain'] = keystone_util.get_project(project_id).domain_id
        user['roles'] = ['admin']
        return keystone_util.create_user(user)

    def _get_cinder_client(self, session):
        """Get cinder client by session"""
        return cinder_client.Client(
            CONF.cinder_client.api_version,
            session=session,
            endpoint_type=CONF.cinder_client.endpoint_type)

    def _swap_volume(self, volume, dest_type):
        """Swap volume to dest_type

           Limitation note: only for compute libvirt driver
        """
        if not dest_type:
            raise exception.Invalid(
                message=(_("destination type is required when "
                           "migration type is swap")))

        if not self._can_swap(volume):
            raise exception.Invalid(
                message=(_("Invalid state for swapping volume")))

        user_info = {
            'name': self.temp_username,
            'password': self.temp_password}
        user = self._create_user(volume, user_info)
        keystone_util = keystone_helper.KeystoneHelper(osc=self.osc)
        try:
            session = keystone_util.create_session(
                user.id, self.temp_password)
            temp_cinder = self._get_cinder_client(session)

            # swap volume
            new_volume = self.cinder_util.create_volume(
                temp_cinder, volume, dest_type)
            self.nova_util.swap_volume(volume, new_volume)

            # delete old volume
            self.cinder_util.delete_volume(volume)

        finally:
            keystone_util.delete_user(user)

        return True

    def _migrate(self, volume_id, dest_node, dest_type):

        try:
            volume = self.cinder_util.get_volume(volume_id)
            if self.migration_type == self.SWAP:
                if dest_node:
                    LOG.warning("dest_node is ignored")
                return self._swap_volume(volume, dest_type)
            elif self.migration_type == self.RETYPE:
                return self.cinder_util.retype(volume, dest_type)
            elif self.migration_type == self.MIGRATE:
                return self.cinder_util.migrate(volume, dest_node)
            else:
                raise exception.Invalid(
                    message=(_("Migration of type '%(migration_type)s' is not "
                               "supported.") %
                             {'migration_type': self.migration_type}))
        except exception.Invalid as ei:
            LOG.exception(ei)
            return False
        except Exception as e:
            LOG.critical("Unexpected exception occurred.")
            LOG.exception(e)
            return False

    def execute(self):
        return self._migrate(self.volume_id,
                             self.destination_node,
                             self.destination_type)

    def revert(self):
        LOG.warning("revert not supported")

    def abort(self):
        pass

    def pre_condition(self):
        pass

    def post_condition(self):
        pass

    def get_description(self):
        return "Moving a volume to destination_node or destination_type"
