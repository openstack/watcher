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

ACTION_PLAN = 'action_plan:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=ACTION_PLAN % 'delete',
        check_str=base.RULE_ADMIN_API,
        description='Delete an action plan.',
        operations=[
            {
                'path': '/v1/action_plans/{action_plan_uuid}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ACTION_PLAN % 'detail',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of action plans with detail.',
        operations=[
            {
                'path': '/v1/action_plans/detail',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ACTION_PLAN % 'get',
        check_str=base.RULE_ADMIN_API,
        description='Get an action plan.',
        operations=[
            {
                'path': '/v1/action_plans/{action_plan_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ACTION_PLAN % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Get all action plans.',
        operations=[
            {
                'path': '/v1/action_plans',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ACTION_PLAN % 'update',
        check_str=base.RULE_ADMIN_API,
        description='Update an action plans.',
        operations=[
            {
                'path': '/v1/action_plans/{action_plan_uuid}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ACTION_PLAN % 'start',
        check_str=base.RULE_ADMIN_API,
        description='Start an action plans.',
        operations=[
            {
                'path': '/v1/action_plans/{action_plan_uuid}/start',
                'method': 'POST'
            }
        ]
    )
]


def list_rules():
    return rules
