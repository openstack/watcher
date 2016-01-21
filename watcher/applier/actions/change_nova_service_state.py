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


from watcher._i18n import _
from watcher.applier.actions import base
from watcher.common import exception
from watcher.common import keystone as kclient
from watcher.common import nova as nclient
from watcher.decision_engine.model import hypervisor_state as hstate


class ChangeNovaServiceState(base.BaseAction):

    @property
    def host(self):
        return self.applies_to

    @property
    def state(self):
        return self.input_parameters.get('state')

    def execute(self):
        target_state = None
        if self.state == hstate.HypervisorState.OFFLINE.value:
            target_state = False
        elif self.status == hstate.HypervisorState.ONLINE.value:
            target_state = True
        return self.nova_manage_service(target_state)

    def revert(self):
        target_state = None
        if self.state == hstate.HypervisorState.OFFLINE.value:
            target_state = True
        elif self.state == hstate.HypervisorState.ONLINE.value:
            target_state = False
        return self.nova_manage_service(target_state)

    def nova_manage_service(self, state):
        if state is None:
            raise exception.IllegalArgumentException(
                message=_("The target state is not defined"))

        keystone = kclient.KeystoneClient()
        wrapper = nclient.NovaClient(keystone.get_credentials(),
                                     session=keystone.get_session())
        if state is True:
            return wrapper.enable_service_nova_compute(self.host)
        else:
            return wrapper.disable_service_nova_compute(self.host)

    def precondition(self):
        pass

    def postcondition(self):
        pass
