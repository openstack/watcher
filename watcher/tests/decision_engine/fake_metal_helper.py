# Copyright (c) 2023 Cloudbase Solutions
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import mock
import uuid

from watcher.common.metal_helper import constants as m_constants


def get_mock_metal_node(node_id=None,
                        power_state=m_constants.PowerState.ON,
                        running_vms=0,
                        hostname=None,
                        compute_state='up'):
    node_id = node_id or str(uuid.uuid4())
    # NOTE(lpetrut): the hostname is important for some of the tests,
    # which expect it to match the fake cluster model.
    hostname = hostname or "compute-" + str(uuid.uuid4()).split('-')[0]

    hypervisor_node_dict = {
        'hypervisor_hostname': hostname,
        'running_vms': running_vms,
        'service': {
            'host': hostname,
        },
        'state': compute_state,
    }
    hypervisor_node = mock.Mock(**hypervisor_node_dict)
    hypervisor_node.to_dict.return_value = hypervisor_node_dict

    node = mock.Mock()
    node.get_power_state.return_value = power_state
    node.get_id.return_value = uuid
    node.get_hypervisor_node.return_value = hypervisor_node
    return node
