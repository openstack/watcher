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
import six
import voluptuous

from watcher._i18n import _
from watcher.applier.actions import base
from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.model import hypervisor_state as hstate


class ChangeNovaServiceState(base.BaseAction):
    """Disables or enables the nova-compute service, deployed on a host

    By using this action, you will be able to update the state of a
    nova-compute service. A disabled nova-compute service can not be selected
    by the nova scheduler for future deployment of server.

    The action schema is::

        schema = Schema({
         'resource_id': str,
         'state': str,
        })

    The `resource_id` references a nova-compute service name (list of available
    nova-compute services is returned by this command: ``nova service-list
    --binary nova-compute``).
    The `state` value should either be `ONLINE` or `OFFLINE`.
    """

    STATE = 'state'

    @property
    def schema(self):
        return voluptuous.Schema({
            voluptuous.Required(self.RESOURCE_ID):
                voluptuous.All(
                    voluptuous.Any(*six.string_types),
                    voluptuous.Length(min=1)),
            voluptuous.Required(self.STATE):
                voluptuous.Any(*[state.value
                                 for state in list(hstate.HypervisorState)]),
        })

    @property
    def host(self):
        return self.resource_id

    @property
    def state(self):
        return self.input_parameters.get(self.STATE)

    def execute(self):
        target_state = None
        if self.state == hstate.HypervisorState.DISABLED.value:
            target_state = False
        elif self.state == hstate.HypervisorState.ENABLED.value:
            target_state = True
        return self._nova_manage_service(target_state)

    def revert(self):
        target_state = None
        if self.state == hstate.HypervisorState.DISABLED.value:
            target_state = True
        elif self.state == hstate.HypervisorState.ENABLED.value:
            target_state = False
        return self._nova_manage_service(target_state)

    def _nova_manage_service(self, state):
        if state is None:
            raise exception.IllegalArgumentException(
                message=_("The target state is not defined"))

        nova = nova_helper.NovaHelper(osc=self.osc)
        if state is True:
            return nova.enable_service_nova_compute(self.host)
        else:
            return nova.disable_service_nova_compute(self.host)

    def precondition(self):
        pass

    def postcondition(self):
        pass
