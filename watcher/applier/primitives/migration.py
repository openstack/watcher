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


from watcher.applier.primitives import base
from watcher.applier import promise
from watcher.common import exception
from watcher.common import keystone as kclient
from watcher.common import nova as nclient


class Migrate(base.BasePrimitive):
    def __init__(self):
        super(Migrate, self).__init__()
        self.instance_uuid = self.applies_to
        self.migration_type = self.input_parameters.get('migration_type')

    def migrate(self, destination):
        keystone = kclient.KeystoneClient()
        wrapper = nclient.NovaClient(keystone.get_credentials(),
                                     session=keystone.get_session())
        instance = wrapper.find_instance(self.instance_uuid)
        if instance:
            if self.migration_type is 'live':
                return wrapper.live_migrate_instance(
                    instance_id=self.instance_uuid, dest_hostname=destination)
            else:
                raise exception.InvalidParameterValue(err=self.migration_type)
        else:
            raise exception.InstanceNotFound(name=self.instance_uuid)

    @promise.Promise
    def execute(self):
        return self.migrate(self.input_parameters.get('dst_hypervisor_uuid'))

    @promise.Promise
    def undo(self):
        return self.migrate(self.input_parameters.get('src_hypervisor_uuid'))
