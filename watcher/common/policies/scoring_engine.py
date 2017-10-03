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

SCORING_ENGINE = 'scoring_engine:%s'

rules = [
    # FIXME(lbragstad): Find someone from watcher to double check this
    # information. This API isn't listed in watcher's API reference
    # documentation.
    policy.DocumentedRuleDefault(
        name=SCORING_ENGINE % 'detail',
        check_str=base.RULE_ADMIN_API,
        description='List scoring engines with details.',
        operations=[
            {
                'path': '/v1/scoring_engines/detail',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): Find someone from watcher to double check this
    # information. This API isn't listed in watcher's API reference
    # documentation.
    policy.DocumentedRuleDefault(
        name=SCORING_ENGINE % 'get',
        check_str=base.RULE_ADMIN_API,
        description='Get a scoring engine.',
        operations=[
            {
                'path': '/v1/scoring_engines/{scoring_engine_id}',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): Find someone from watcher to double check this
    # information. This API isn't listed in watcher's API reference
    # documentation.
    policy.DocumentedRuleDefault(
        name=SCORING_ENGINE % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Get all scoring engines.',
        operations=[
            {
                'path': '/v1/scoring_engines',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
