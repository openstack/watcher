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

AUDIT_TEMPLATE = 'audit_template:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=AUDIT_TEMPLATE % 'create',
        check_str=base.RULE_ADMIN_API,
        description='Create an audit template.',
        operations=[
            {
                'path': '/v1/audit_templates',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT_TEMPLATE % 'delete',
        check_str=base.RULE_ADMIN_API,
        description='Delete an audit template.',
        operations=[
            {
                'path': '/v1/audit_templates/{audit_template_uuid}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT_TEMPLATE % 'detail',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of audit templates with details.',
        operations=[
            {
                'path': '/v1/audit_templates/detail',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT_TEMPLATE % 'get',
        check_str=base.RULE_ADMIN_API,
        description='Get an audit template.',
        operations=[
            {
                'path': '/v1/audit_templates/{audit_template_uuid}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT_TEMPLATE % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Get a list of all audit templates.',
        operations=[
            {
                'path': '/v1/audit_templates',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=AUDIT_TEMPLATE % 'update',
        check_str=base.RULE_ADMIN_API,
        description='Update an audit template.',
        operations=[
            {
                'path': '/v1/audit_templates/{audit_template_uuid}',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules
