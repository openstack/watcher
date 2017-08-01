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

from watcher.decision_engine.scoring import scoring_factory
from watcher.tests import base


class TestScoringFactory(base.TestCase):

    def test_get_scoring_engine(self):
        scorer = scoring_factory.get_scoring_engine('dummy_scorer')
        self.assertEqual('dummy_scorer', scorer.get_name())

        scorer = scoring_factory.get_scoring_engine('dummy_min_scorer')
        self.assertEqual('dummy_min_scorer', scorer.get_name())

        scorer = scoring_factory.get_scoring_engine('dummy_max_scorer')
        self.assertEqual('dummy_max_scorer', scorer.get_name())

        scorer = scoring_factory.get_scoring_engine('dummy_avg_scorer')
        self.assertEqual('dummy_avg_scorer', scorer.get_name())

        self.assertRaises(
            KeyError,
            scoring_factory.get_scoring_engine,
            'non_existing_scorer')

    def test_get_scoring_engine_list(self):
        scoring_engines = scoring_factory.get_scoring_engine_list()

        engine_names = {'dummy_scorer', 'dummy_min_scorer',
                        'dummy_max_scorer', 'dummy_avg_scorer'}

        for scorer in scoring_engines:
            self.assertIn(scorer.get_name(), engine_names)
