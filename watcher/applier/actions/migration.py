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

from watcher.applier.actions import base
from watcher.common import exception
from watcher.common import keystone as kclient
from watcher.common import nova as nclient

LOG = log.getLogger(__name__)


class Migrate(base.BaseAction):
    @property
    def instance_uuid(self):
        return self.applies_to

    @property
    def migration_type(self):
        return self.input_parameters.get('migration_type')

    @property
    def dst_hypervisor(self):
        return self.input_parameters.get('dst_hypervisor')

    @property
    def src_hypervisor(self):
        return self.input_parameters.get('src_hypervisor')

    def migrate(self, destination):
        keystone = kclient.KeystoneClient()
        wrapper = nclient.NovaClient(keystone.get_credentials(),
                                     session=keystone.get_session())
        LOG.debug("Migrate instance %s to %s  ", self.instance_uuid,
                  destination)
        instance = wrapper.find_instance(self.instance_uuid)
        if instance:
            if self.migration_type == 'live':
                return wrapper.live_migrate_instance(
                    instance_id=self.instance_uuid, dest_hostname=destination)
            else:
                raise exception.InvalidParameterValue(err=self.migration_type)
        else:
            raise exception.InstanceNotFound(name=self.instance_uuid)

    def execute(self):
        return self.migrate(destination=self.dst_hypervisor)

    def revert(self):
        return self.migrate(destination=self.src_hypervisor)

    def precondition(self):
        # todo(jed) check if the instance exist/ check if the instance is on
        # the src_hypervisor
        pass

    def postcondition(self):
        # todo(jed) we can image to check extra parameters (nework reponse,ect)
        pass
