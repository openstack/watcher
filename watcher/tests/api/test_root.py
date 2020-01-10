# Copyright 2013 Red Hat, Inc.
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

from watcher.tests.api import base


class TestRoot(base.FunctionalTest):

    def test_get_root(self):
        data = self.get_json('/', path_prefix='')
        self.assertEqual('v1', data['default_version']['id'])
        # Check fields are not empty
        [self.assertNotIn(f, ['', []]) for f in data.keys()]


class TestV1Root(base.FunctionalTest):

    def test_get_v1_root_all(self):
        data = self.get_json(
            '/', headers={'OpenStack-API-Version': 'infra-optim 1.4'})
        self.assertEqual('v1', data['id'])
        # Check fields are not empty
        for f in data.keys():
            self.assertNotIn(f, ['', []])
        # Check if all known resources are present and there are no extra ones.
        not_resources = ('id', 'links', 'media_types')
        actual_resources = tuple(set(data.keys()) - set(not_resources))
        expected_resources = ('audit_templates', 'audits', 'actions',
                              'action_plans', 'data_model', 'scoring_engines',
                              'services', 'webhooks')
        self.assertEqual(sorted(expected_resources), sorted(actual_resources))

        self.assertIn({'type': 'application/vnd.openstack.watcher.v1+json',
                       'base': 'application/json'}, data['media_types'])

    def test_get_v1_root_without_datamodel(self):
        data = self.get_json(
            '/', headers={'OpenStack-API-Version': 'infra-optim 1.2'})
        self.assertEqual('v1', data['id'])
        # Check fields are not empty
        for f in data.keys():
            self.assertNotIn(f, ['', []])
        # Check if all known resources are present and there are no extra ones.
        not_resources = ('id', 'links', 'media_types')
        actual_resources = tuple(set(data.keys()) - set(not_resources))
        expected_resources = ('audit_templates', 'audits', 'actions',
                              'action_plans', 'scoring_engines',
                              'services')
        self.assertEqual(sorted(expected_resources), sorted(actual_resources))

        self.assertIn({'type': 'application/vnd.openstack.watcher.v1+json',
                       'base': 'application/json'}, data['media_types'])
