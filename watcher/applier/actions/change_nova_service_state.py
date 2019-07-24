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
from watcher.common import nova_helper
from watcher.decision_engine.model import element


class ChangeNovaServiceState(base.BaseAction):
    """Disables or enables the nova-compute service, deployed on a host

    By using this action, you will be able to update the state of a
    nova-compute service. A disabled nova-compute service can not be selected
    by the nova scheduler for future deployment of server.

    The action schema is::

        schema = Schema({
         'resource_id': str,
         'state': str,
         'disabled_reason': str,
        })

    The `resource_id` references a nova-compute service name (list of available
    nova-compute services is returned by this command: ``nova service-list
    --binary nova-compute``).
    The `state` value should either be `ONLINE` or `OFFLINE`.
    The `disabled_reason` references the reason why Watcher disables this
    nova-compute service. The value should be with `watcher_` prefix, such as
    `watcher_disabled`, `watcher_maintaining`.
    """

    STATE = 'state'
    REASON = 'disabled_reason'
    RESOURCE_NAME = 'resource_name'

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'resource_id': {
                    'type': 'string',
                    "minlength": 1
                },
                'resource_name': {
                    'type': 'string',
                    "minlength": 1
                },
                'state': {
                    'type': 'string',
                    'enum': [element.ServiceState.ONLINE.value,
                             element.ServiceState.OFFLINE.value,
                             element.ServiceState.ENABLED.value,
                             element.ServiceState.DISABLED.value]
                },
                'disabled_reason': {
                    'type': 'string',
                    "minlength": 1
                }
            },
            'required': ['resource_id', 'state'],
            'additionalProperties': False,
        }

    @property
    def host(self):
        return self.input_parameters.get(self.RESOURCE_NAME)

    @property
    def state(self):
        return self.input_parameters.get(self.STATE)

    @property
    def reason(self):
        return self.input_parameters.get(self.REASON)

    def execute(self):
        target_state = None
        if self.state == element.ServiceState.DISABLED.value:
            target_state = False
        elif self.state == element.ServiceState.ENABLED.value:
            target_state = True
        return self._nova_manage_service(target_state)

    def revert(self):
        target_state = None
        if self.state == element.ServiceState.DISABLED.value:
            target_state = True
        elif self.state == element.ServiceState.ENABLED.value:
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
            return nova.disable_service_nova_compute(self.host, self.reason)

    def pre_condition(self):
        pass

    def post_condition(self):
        pass

    def get_description(self):
        """Description of the action"""
        return ("Disables or enables the nova-compute service."
                "A disabled nova-compute service can not be selected "
                "by the nova for future deployment of new server.")
