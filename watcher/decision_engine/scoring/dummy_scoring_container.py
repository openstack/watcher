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
#

from oslo_log import log
from oslo_serialization import jsonutils

from watcher._i18n import _
from watcher.decision_engine.scoring import base

LOG = log.getLogger(__name__)


class DummyScoringContainer(base.ScoringEngineContainer):
    """Sample Scoring Engine container returning a list of scoring engines.

    Please note that it can be used in dynamic scenarios and the returned list
    might return instances based on some external configuration (e.g. in
    database). In order for these scoring engines to become discoverable in
    Watcher API and Watcher CLI, a database re-sync is required. It can be
    executed using watcher-sync tool for example.
    """

    @classmethod
    def get_scoring_engine_list(cls):
        return [
            SimpleFunctionScorer(
                'dummy_min_scorer',
                'Dummy Scorer calculating the minimum value',
                min),
            SimpleFunctionScorer(
                'dummy_max_scorer',
                'Dummy Scorer calculating the maximum value',
                max),
            SimpleFunctionScorer(
                'dummy_avg_scorer',
                'Dummy Scorer calculating the average value',
                lambda x: float(sum(x)) / len(x)),
        ]


class SimpleFunctionScorer(base.ScoringEngine):
    """A simple generic scoring engine for demonstration purposes only.

    A generic scoring engine implementation, which is expecting a JSON
    formatted array of numbers to be passed as an input for score calculation.
    It then executes the aggregate function on this array and returns an
    array with a single aggregated number (also JSON formatted).
    """

    def __init__(self, name, description, aggregate_function):
        super(SimpleFunctionScorer, self).__init__(config=None)
        self._name = name
        self._description = description
        self._aggregate_function = aggregate_function

    def get_name(self):
        return self._name

    def get_description(self):
        return self._description

    def get_metainfo(self):
        return ''

    def calculate_score(self, features):
        LOG.debug('Calculating score, features: %s', features)

        # Basic input validation
        try:
            flist = jsonutils.loads(features)
        except Exception as e:
            raise ValueError(_('Unable to parse features: %s') % e)
        if type(flist) is not list:
            raise ValueError(_('JSON list expected in feature argument'))
        if len(flist) < 1:
            raise ValueError(_('At least one feature is required'))

        # Calculate the result
        result = self._aggregate_function(flist)

        # Return the aggregated result
        return jsonutils.dumps([result])
