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

from watcher.applier.primitives.base import BasePrimitive
from watcher.applier.primitives.wrapper.nova_wrapper import NovaWrapper
from watcher.applier.promise import Promise
from watcher.common.exception import IllegalArgumentException
from watcher.common.keystone import KeystoneClient
from watcher.decision_engine.model.hypervisor_state import HypervisorState

CONF = cfg.CONF


class ChangeNovaServiceState(BasePrimitive):
    def __init__(self, host, state):
        """This class allows us to change the state of nova-compute service.

        :param host: the uuid of the host
        :param state: (enabled/disabled)
        """
        super(BasePrimitive, self).__init__()
        self._host = host
        self._state = state

    @property
    def host(self):
        return self._host

    @property
    def state(self):
        return self._state

    @Promise
    def execute(self):
        target_state = None
        if self.state == HypervisorState.OFFLINE.value:
            target_state = False
        elif self.status == HypervisorState.ONLINE.value:
            target_state = True
        return self.nova_manage_service(target_state)

    @Promise
    def undo(self):
        target_state = None
        if self.state == HypervisorState.OFFLINE.value:
            target_state = True
        elif self.state == HypervisorState.ONLINE.value:
            target_state = False
        return self.nova_manage_service(target_state)

    def nova_manage_service(self, state):
        if state is None:
            raise IllegalArgumentException("The target state is not defined")

        keystone = KeystoneClient()
        wrapper = NovaWrapper(keystone.get_credentials(),
                              session=keystone.get_session())
        if state is True:
            return wrapper.enable_service_nova_compute(self.host)
        else:
            return wrapper.disable_service_nova_compute(self.host)
