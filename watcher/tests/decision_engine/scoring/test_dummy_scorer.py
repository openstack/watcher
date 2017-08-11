# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel
#
# Authors: Tomasz Kaczynski <tomasz.kaczynski@intel.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_serialization import jsonutils

from watcher.decision_engine.scoring import dummy_scorer
from watcher.tests import base


class TestDummyScorer(base.TestCase):

    def test_metadata(self):
        scorer = dummy_scorer.DummyScorer(config=None)
        self.assertEqual('dummy_scorer', scorer.get_name())
        self.assertIn('Dummy', scorer.get_description())

        metainfo = scorer.get_metainfo()
        self.assertIn('feature_columns', metainfo)
        self.assertIn('result_columns', metainfo)
        self.assertIn('workloads', metainfo)

    def test_calculate_score(self):
        scorer = dummy_scorer.DummyScorer(config=None)

        self._assert_result(scorer, 0, '[0, 0, 0, 0, 0, 0, 0, 0, 0]')
        self._assert_result(scorer, 0, '[50, 0, 0, 600, 0, 0, 0, 0, 0]')
        self._assert_result(scorer, 0, '[0, 0, 0, 0, 600, 0, 0, 0, 0]')
        self._assert_result(scorer, 1, '[85, 0, 0, 0, 0, 0, 0, 0, 0]')
        self._assert_result(scorer, 2, '[0, 0, 0, 1100, 1100, 0, 0, 0, 0]')
        self._assert_result(scorer, 3,
                            '[0, 0, 0, 0, 0, 70000000, 70000000, 0, 0]')

    def _assert_result(self, scorer, expected, features):
        result_str = scorer.calculate_score(features)
        actual_result = jsonutils.loads(result_str)[0]
        self.assertEqual(expected, actual_result)
