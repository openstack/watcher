# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica
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

from watcher_tempest_plugin.tests.api.admin import base


class TestShowListService(base.BaseInfraOptimTest):
    """Tests for services"""

    DECISION_ENGINE = "watcher-decision-engine"
    APPLIER = "watcher-applier"

    @classmethod
    def resource_setup(cls):
        super(TestShowListService, cls).resource_setup()

    def assert_expected(self, expected, actual,
                        keys=('created_at', 'updated_at', 'deleted_at')):
        super(TestShowListService, self).assert_expected(
            expected, actual, keys)

    @test.attr(type='smoke')
    def test_show_service(self):
        _, service = self.client.show_service(self.DECISION_ENGINE)

        self.assertEqual(self.DECISION_ENGINE, service['name'])
        self.assertIn("host", service.keys())
        self.assertIn("last_seen_up", service.keys())
        self.assertIn("status", service.keys())

    @test.attr(type='smoke')
    def test_show_service_with_links(self):
        _, service = self.client.show_service(self.DECISION_ENGINE)
        self.assertIn('links', service.keys())
        self.assertEqual(2, len(service['links']))
        self.assertIn(str(service['id']),
                      service['links'][0]['href'])

    @test.attr(type="smoke")
    def test_list_services(self):
        _, body = self.client.list_services()
        self.assertIn('services', body)
        services = body['services']
        self.assertIn(self.DECISION_ENGINE,
                      [i['name'] for i in body['services']])

        for service in services:
            self.assertTrue(
                all(val is not None for key, val in service.items()
                    if key in ['id', 'name', 'host', 'status',
                               'last_seen_up']))

        # Verify self links.
        for service in body['services']:
            self.validate_self_link('services', service['id'],
                                    service['links'][0]['href'])
