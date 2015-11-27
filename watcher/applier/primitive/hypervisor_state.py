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


from oslo_config import cfg

from watcher.applier.primitive.base import PrimitiveCommand
from watcher.applier.primitive.wrapper.nova_wrapper import NovaWrapper
from watcher.applier.promise import Promise

from watcher.common.keystone import KeystoneClient
from watcher.decision_engine.model.hypervisor_state import HypervisorState

CONF = cfg.CONF


class HypervisorStateCommand(PrimitiveCommand):
    def __init__(self, host, status):
        self.host = host
        self.status = status

    def nova_manage_service(self, status):
        keystone = KeystoneClient()
        wrapper = NovaWrapper(keystone.get_credentials(),
                              session=keystone.get_session())
        if status is True:
            return wrapper.enable_service_nova_compute(self.host)
        else:
            return wrapper.disable_service_nova_compute(self.host)

    @Promise
    def execute(self):
        if self.status == HypervisorState.OFFLINE.value:
            state = False
        elif self.status == HypervisorState.ONLINE.value:
            state = True
        return self.nova_manage_service(state)

    @Promise
    def undo(self):
        if self.status == HypervisorState.OFFLINE.value:
            state = True
        elif self.status == HypervisorState.ONLINE.value:
            state = False
        return self.nova_manage_service(state)
