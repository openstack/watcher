# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
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

"""Tests for manipulating Audit via the DB API"""

import six
from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


class DbAuditTestCase(base.DbTestCase):

    def _create_test_audit(self, **kwargs):
        audit = utils.get_test_audit(**kwargs)
        self.dbapi.create_audit(audit)
        return audit

    def test_get_audit_list(self):
        uuids = []
        for i in range(1, 6):
            audit = utils.create_test_audit(uuid=w_utils.generate_uuid())
            uuids.append(six.text_type(audit['uuid']))
        res = self.dbapi.get_audit_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(uuids.sort(), res_uuids.sort())

    def test_get_audit_list_with_filters(self):
        audit1 = self._create_test_audit(
            id=1,
            type='ONESHOT',
            uuid=w_utils.generate_uuid(),
            deadline=None,
            state='ONGOING')
        audit2 = self._create_test_audit(
            id=2,
            type='CONTINUOUS',
            uuid=w_utils.generate_uuid(),
            deadline=None,
            state='PENDING')

        res = self.dbapi.get_audit_list(self.context,
                                        filters={'type': 'ONESHOT'})
        self.assertEqual([audit1['id']], [r.id for r in res])

        res = self.dbapi.get_audit_list(self.context,
                                        filters={'type': 'bad-type'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'state': 'ONGOING'})
        self.assertEqual([audit1['id']], [r.id for r in res])

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'state': 'PENDING'})
        self.assertEqual([audit2['id']], [r.id for r in res])

    def test_get_audit_by_id(self):
        audit = self._create_test_audit()
        audit = self.dbapi.get_audit_by_id(self.context, audit['id'])
        self.assertEqual(audit['uuid'], audit.uuid)

    def test_get_audit_by_uuid(self):
        audit = self._create_test_audit()
        audit = self.dbapi.get_audit_by_uuid(self.context, audit['uuid'])
        self.assertEqual(audit['id'], audit.id)

    def test_get_audit_that_does_not_exist(self):
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.get_audit_by_id, self.context, 1234)

    def test_get_audit_list_with_filter_by_audit_template_uuid(self):

        audit_template = self.dbapi.create_audit_template(
            utils.get_test_audit_template(
                uuid=w_utils.generate_uuid(),
                name='My Audit Template 1',
                description='Description of my audit template 1',
                host_aggregate=5,
                goal='SERVERS_CONSOLIDATION',
                extra={'automatic': True})
        )

        audit = self._create_test_audit(
            type='ONESHOT',
            uuid=w_utils.generate_uuid(),
            deadline=None,
            state='ONGOING',
            audit_template_id=audit_template.id)

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'audit_template_uuid': audit_template.uuid})

        for r in res:
            self.assertEqual(audit['audit_template_id'], r.audit_template_id)

    def test_get_audit_list_with_filter_by_audit_template_name(self):

        audit_template = self.dbapi.create_audit_template(
            utils.get_test_audit_template(
                uuid=w_utils.generate_uuid(),
                name='My Audit Template 1',
                description='Description of my audit template 1',
                host_aggregate=5,
                goal='SERVERS_CONSOLIDATION',
                extra={'automatic': True})
        )

        audit = self._create_test_audit(
            type='ONESHOT',
            uuid=w_utils.generate_uuid(),
            deadline=None,
            state='ONGOING',
            audit_template_id=audit_template.id)

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'audit_template_name': audit_template.name})

        for r in res:
            self.assertEqual(audit['audit_template_id'], r.audit_template_id)

    def test_update_audit(self):
        audit = self._create_test_audit()
        res = self.dbapi.update_audit(audit['id'], {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_audit_that_does_not_exist(self):
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.update_audit, 1234, {'name': ''})

    def test_update_audit_uuid(self):
        audit = self._create_test_audit()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_audit, audit['id'],
                          {'uuid': 'hello'})

    def test_destroy_audit(self):
        audit = self._create_test_audit()
        self.dbapi.destroy_audit(audit['id'])
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.get_audit_by_id,
                          self.context, audit['id'])

    def test_destroy_audit_by_uuid(self):
        uuid = w_utils.generate_uuid()
        self._create_test_audit(uuid=uuid)
        self.assertIsNotNone(self.dbapi.get_audit_by_uuid(self.context,
                                                          uuid))
        self.dbapi.destroy_audit(uuid)
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.get_audit_by_uuid, self.context, uuid)

    def test_destroy_audit_that_does_not_exist(self):
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.destroy_audit, 1234)

    def test_destroy_audit_that_referenced_by_action_plans(self):
        audit = self._create_test_audit()
        action_plan = utils.create_test_action_plan(audit_id=audit['id'])
        self.assertEqual(audit['id'], action_plan.audit_id)
        self.assertRaises(exception.AuditReferenced,
                          self.dbapi.destroy_audit, audit['id'])

    def test_create_audit_already_exists(self):
        uuid = w_utils.generate_uuid()
        self._create_test_audit(id=1, uuid=uuid)
        self.assertRaises(exception.AuditAlreadyExists,
                          self._create_test_audit,
                          id=2, uuid=uuid)
