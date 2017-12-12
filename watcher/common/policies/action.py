# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_policy import policy

from watcher.common.policies import base

ACTION = 'action:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=ACTION % 'detail',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of actions with detail.',
        operations=[
            {
                'path': '/v1/actions/detail',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ACTION % 'get',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve information about a given action.',
        operations=[
            {
                'path': '/v1/actions/{action_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ACTION % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of all actions.',
        operations=[
            {
                'path': '/v1/actions',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
