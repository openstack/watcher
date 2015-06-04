# -*- encoding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Utils for testing the API service.
"""

import datetime
import json

from watcher.api.controllers.v1 import action as action_ctrl
from watcher.api.controllers.v1 import action_plan as action_plan_ctrl
from watcher.api.controllers.v1 import audit as audit_ctrl
from watcher.api.controllers.v1 import audit_template as audit_template_ctrl
from watcher.tests.db import utils as db_utils


ADMIN_TOKEN = '4562138218392831'
MEMBER_TOKEN = '4562138218392832'


class FakeMemcache(object):
    """Fake cache that is used for keystone tokens lookup."""

    _cache = {
        'tokens/%s' % ADMIN_TOKEN: {
            'access': {
                'token': {'id': ADMIN_TOKEN,
                          'expires': '2100-09-11T00:00:00'},
                'user': {'id': 'user_id1',
                         'name': 'user_name1',
                         'tenantId': '123i2910',
                         'tenantName': 'mytenant',
                         'roles': [{'name': 'admin'}]
                         },
            }
        },
        'tokens/%s' % MEMBER_TOKEN: {
            'access': {
                'token': {'id': MEMBER_TOKEN,
                          'expires': '2100-09-11T00:00:00'},
                'user': {'id': 'user_id2',
                         'name': 'user-good',
                         'tenantId': 'project-good',
                         'tenantName': 'goodies',
                         'roles': [{'name': 'Member'}]
                         }
            }
        }
    }

    def __init__(self):
        self.set_key = None
        self.set_value = None
        self.token_expiration = None

    def get(self, key):
        dt = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        return json.dumps((self._cache.get(key), dt.isoformat()))

    def set(self, key, value, time=0, min_compress_len=0):
        self.set_value = value
        self.set_key = key


def remove_internal(values, internal):
    # NOTE(yuriyz): internal attributes should not be posted, except uuid
    int_attr = [attr.lstrip('/') for attr in internal if attr != '/uuid']
    return dict([(k, v) for (k, v) in values.iteritems() if k not in int_attr])


def audit_post_data(**kw):
    audit = db_utils.get_test_audit(**kw)
    internal = audit_ctrl.AuditPatchType.internal_attrs()
    return remove_internal(audit, internal)


def audit_template_post_data(**kw):
    audit_template = db_utils.get_test_audit_template(**kw)
    internal = audit_template_ctrl.AuditTemplatePatchType.internal_attrs()
    return remove_internal(audit_template, internal)


def action_post_data(**kw):
    action = db_utils.get_test_action(**kw)
    internal = action_ctrl.ActionPatchType.internal_attrs()
    return remove_internal(action, internal)


def action_plan_post_data(**kw):
    act_plan = db_utils.get_test_action_plan(**kw)
    internal = action_plan_ctrl.ActionPlanPatchType.internal_attrs()
    return remove_internal(act_plan, internal)
