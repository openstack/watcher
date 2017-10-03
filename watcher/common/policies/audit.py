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

AUDIT = 'audit:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=AUDIT % 'create',
        check_str=base.RULE_ADMIN_API,
        description='Create a new audit.',
        operations=[
            {
                'path': '/v1/audits',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT % 'delete',
        check_str=base.RULE_ADMIN_API,
        description='Delete an audit.',
        operations=[
            {
                'path': '/v1/audits/{audit_uuid}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT % 'detail',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve audit list with details.',
        operations=[
            {
                'path': '/v1/audits/detail',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT % 'get',
        check_str=base.RULE_ADMIN_API,
        description='Get an audit.',
        operations=[
            {
                'path': '/v1/audits/{audit_uuid}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Get all audits.',
        operations=[
            {
                'path': '/v1/audits',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT % 'update',
        check_str=base.RULE_ADMIN_API,
        description='Update an audit.',
        operations=[
            {
                'path': '/v1/audits/{audit_uuid}',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules
