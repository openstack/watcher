# Copyright (c) 2012 OpenStack Foundation
#
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


policy_data = """
{
    "admin_api": "role:admin or role:administrator",
    "show_password": "!",
    "default": "rule:admin_api",

    "action:detail": "",
    "action:get": "",
    "action:get_all": "",

    "action_plan:delete": "",
    "action_plan:detail": "",
    "action_plan:get": "",
    "action_plan:get_all": "",
    "action_plan:update": "",

    "audit:create": "",
    "audit:delete": "",
    "audit:detail": "",
    "audit:get": "",
    "audit:get_all": "",
    "audit:update": "",

    "audit_template:create": "",
    "audit_template:delete": "",
    "audit_template:detail": "",
    "audit_template:get": "",
    "audit_template:get_all": "",
    "audit_template:update": "",

    "goal:detail": "",
    "goal:get": "",
    "goal:get_all": "",

    "scoring_engine:detail": "",
    "scoring_engine:get": "",
    "scoring_engine:get_all": "",

    "strategy:detail": "",
    "strategy:get": "",
    "strategy:get_all": "",
    "strategy:state": "",

    "service:detail": "",
    "service:get": "",
    "service:get_all": "",

    "data_model:get_all": ""
}
"""


policy_data_compat_juno = """
{
    "admin": "role:admin or role:administrator",
    "admin_api": "is_admin:True",
    "default": "rule:admin_api"
}
"""


def get_policy_data(compat):
    if not compat:
        return policy_data
    elif compat == 'juno':
        return policy_data_compat_juno
    else:
        raise Exception('Policy data for %s not available' % compat)
