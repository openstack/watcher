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

from watcher_tempest_plugin.tests.api.admin import base


class TestShowListScoringEngine(base.BaseInfraOptimTest):
    """Tests for scoring engines"""

    DUMMY_SCORING_ENGINE = "dummy_scorer"

    @classmethod
    def resource_setup(cls):
        super(TestShowListScoringEngine, cls).resource_setup()

    def assert_expected(self, expected, actual,
                        keys=('created_at', 'updated_at', 'deleted_at')):
        super(TestShowListScoringEngine, self).assert_expected(
            expected, actual, keys)

    @test.attr(type='smoke')
    def test_show_scoring_engine(self):
        _, scoring_engine = self.client.show_scoring_engine(
            self.DUMMY_SCORING_ENGINE)

        self.assertEqual(self.DUMMY_SCORING_ENGINE, scoring_engine['name'])

        expected_fields = {'metainfo', 'description', 'name', 'uuid', 'links'}
        self.assertEqual(expected_fields, set(scoring_engine.keys()))

    @test.attr(type='smoke')
    def test_show_scoring_engine_with_links(self):
        _, scoring_engine = self.client.show_scoring_engine(
            self.DUMMY_SCORING_ENGINE)
        self.assertIn('links', scoring_engine.keys())
        self.assertEqual(2, len(scoring_engine['links']))
        self.assertIn(scoring_engine['uuid'],
                      scoring_engine['links'][0]['href'])

    @test.attr(type="smoke")
    def test_list_scoring_engines(self):
        _, body = self.client.list_scoring_engines()
        self.assertIn(self.DUMMY_SCORING_ENGINE,
                      [i['name'] for i in body['scoring_engines']])

        # Verify self links.
        for scoring_engine in body['scoring_engines']:
            self.validate_self_link('scoring_engines', scoring_engine['uuid'],
                                    scoring_engine['links'][0]['href'])
