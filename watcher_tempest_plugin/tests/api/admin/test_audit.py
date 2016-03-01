# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

from __future__ import unicode_literals

from tempest import test
from tempest_lib import decorators
from tempest_lib import exceptions as lib_exc

from watcher_tempest_plugin.tests.api.admin import base


class TestCreateUpdateDeleteAudit(base.BaseInfraOptimTest):
    """Tests for audit."""

    def assert_expected(self, expected, actual,
                        keys=('created_at', 'updated_at',
                              'deleted_at', 'state')):
        super(TestCreateUpdateDeleteAudit, self).assert_expected(
            expected, actual, keys)

    @test.attr(type='smoke')
    def test_create_audit_oneshot(self):
        _, audit_template = self.create_audit_template()

        audit_params = dict(
            audit_template_uuid=audit_template['uuid'],
            type='ONESHOT',
        )

        _, body = self.create_audit(**audit_params)
        self.assert_expected(audit_params, body)

        _, audit = self.client.show_audit(body['uuid'])
        self.assert_expected(audit, body)

    @test.attr(type='smoke')
    def test_create_audit_continuous(self):
        _, audit_template = self.create_audit_template()

        audit_params = dict(
            audit_template_uuid=audit_template['uuid'],
            type='CONTINUOUS',
        )

        _, body = self.create_audit(**audit_params)
        self.assert_expected(audit_params, body)

        _, audit = self.client.show_audit(body['uuid'])
        self.assert_expected(audit, body)

    @test.attr(type='smoke')
    def test_create_audit_with_wrong_audit_template(self):
        audit_params = dict(
            audit_template_uuid='INVALID',
            type='ONESHOT',
        )

        self.assertRaises(
            lib_exc.BadRequest, self.create_audit, **audit_params)

    @decorators.skip_because(bug="1532843")
    @test.attr(type='smoke')
    def test_create_audit_with_invalid_state(self):
        _, audit_template = self.create_audit_template()

        audit_params = dict(
            audit_template_uuid=audit_template['uuid'],
            state='INVALID',
        )

        self.assertRaises(
            lib_exc.BadRequest, self.create_audit, **audit_params)

    @decorators.skip_because(bug="1533210")
    @test.attr(type='smoke')
    def test_create_audit_with_no_state(self):
        _, audit_template = self.create_audit_template()

        audit_params = dict(
            audit_template_uuid=audit_template['uuid'],
            state='',
        )

        _, body = self.create_audit(**audit_params)
        self.assert_expected(audit_params, body)

        _, audit = self.client.show_audit(body['uuid'])

        initial_audit_state = audit.pop('state')
        self.assertEqual('PENDING', initial_audit_state)

        self.assert_expected(audit, body)

    @test.attr(type='smoke')
    def test_delete_audit(self):
        _, audit_template = self.create_audit_template()
        _, body = self.create_audit(audit_template['uuid'])
        audit_uuid = body['uuid']

        self.delete_audit(audit_uuid)

        self.assertRaises(lib_exc.NotFound, self.client.show_audit, audit_uuid)


class TestShowListAudit(base.BaseInfraOptimTest):
    """Tests for audit."""

    audit_states = ['ONGOING', 'SUCCEEDED', 'SUBMITTED', 'FAILED',
                    'CANCELLED', 'DELETED', 'PENDING']

    @classmethod
    def resource_setup(cls):
        super(TestShowListAudit, cls).resource_setup()
        _, cls.audit_template = cls.create_audit_template()
        _, cls.audit = cls.create_audit(cls.audit_template['uuid'])

    def assert_expected(self, expected, actual,
                        keys=('created_at', 'updated_at',
                              'deleted_at', 'state')):
        super(TestShowListAudit, self).assert_expected(
            expected, actual, keys)

    @test.attr(type='smoke')
    def test_show_audit(self):
        _, audit = self.client.show_audit(
            self.audit['uuid'])

        initial_audit = self.audit.copy()
        del initial_audit['state']
        audit_state = audit['state']
        actual_audit = audit.copy()
        del actual_audit['state']

        self.assertIn(audit_state, self.audit_states)
        self.assert_expected(initial_audit, actual_audit)

    @test.attr(type='smoke')
    def test_show_audit_with_links(self):
        _, audit = self.client.show_audit(
            self.audit['uuid'])
        self.assertIn('links', audit.keys())
        self.assertEqual(2, len(audit['links']))
        self.assertIn(audit['uuid'],
                      audit['links'][0]['href'])

    @test.attr(type="smoke")
    def test_list_audits(self):
        _, body = self.client.list_audits()
        self.assertIn(self.audit['uuid'],
                      [i['uuid'] for i in body['audits']])
        # Verify self links.
        for audit in body['audits']:
            self.validate_self_link('audits', audit['uuid'],
                                    audit['links'][0]['href'])

    @test.attr(type='smoke')
    def test_list_with_limit(self):
        # We create 3 extra audits to exceed the limit we fix
        for _ in range(3):
            self.create_audit(self.audit_template['uuid'])

        _, body = self.client.list_audits(limit=3)

        next_marker = body['audits'][-1]['uuid']
        self.assertEqual(3, len(body['audits']))
        self.assertIn(next_marker, body['next'])

    @test.attr(type='smoke')
    def test_list_audits_related_to_given_audit_template(self):
        _, body = self.client.list_audits(
            audit_template=self.audit_template['uuid'])
        self.assertIn(self.audit['uuid'], [n['uuid'] for n in body['audits']])
