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

from watcher.decision_engine.scoring import dummy_scoring_container
from watcher.tests import base


class TestDummyScoringContainer(base.TestCase):

    def test_get_scoring_engine_list(self):
        scorers = (dummy_scoring_container.DummyScoringContainer
                                          .get_scoring_engine_list())

        self.assertEqual(3, len(scorers))
        self.assertEqual('dummy_min_scorer', scorers[0].get_name())
        self.assertEqual('dummy_max_scorer', scorers[1].get_name())
        self.assertEqual('dummy_avg_scorer', scorers[2].get_name())

    def test_scorers(self):
        scorers = (dummy_scoring_container.DummyScoringContainer
                                          .get_scoring_engine_list())

        self._assert_result(scorers[0], 1.1, '[1.1, 2.2, 4, 8]')
        self._assert_result(scorers[1], 8, '[1.1, 2.2, 4, 8]')
        # float(1 + 2 + 4 + 8) / 4 = 15.0 / 4 = 3.75
        self._assert_result(scorers[2], 3.75, '[1, 2, 4, 8]')

    def _assert_result(self, scorer, expected, features):
        result_str = scorer.calculate_score(features)
        actual_result = jsonutils.loads(result_str)[0]
        self.assertEqual(expected, actual_result)
