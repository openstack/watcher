# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

import numbers

from oslo_log import log

from watcher._i18n import _
from watcher.common import exception
from watcher.common import utils

LOG = log.getLogger(__name__)


class IndicatorsMap(utils.Struct):
    pass


class Indicator(utils.Struct):

    def __init__(self, name, description, unit, value):
        super(Indicator, self).__init__()
        self.name = name
        self.description = description
        self.unit = unit
        if not isinstance(value, numbers.Number):
            raise exception.InvalidIndicatorValue(
                _("An indicator value should be a number"))
        self.value = value


class Efficacy(object):
    """Solution efficacy"""

    def __init__(self, goal, strategy):
        """Solution efficacy

        :param goal: Goal associated to this solution
        :type goal: :py:class:`~.base.Goal` instance
        :param strategy: Strategy associated to this solution
        :type strategy: :py:class:`~.BaseStrategy` instance
        """
        self.goal = goal
        self.strategy = strategy

        self._efficacy_spec = self.goal.efficacy_specification

        # Used to store in DB the info related to the efficacy indicators
        self.indicators = []
        # Used to compute the global efficacy
        self._indicators_mapping = IndicatorsMap()
        self.global_efficacy = []

    def set_efficacy_indicators(self, **indicators_map):
        """Set the efficacy indicators

        :param indicators_map: kwargs where the key is the name of the efficacy
                               indicator as defined in the associated
                               :py:class:`~.IndicatorSpecification` and the
                               value is a number.
        :type indicators_map: dict {str: numerical value}
        """
        self._indicators_mapping.update(indicators_map)

    def compute_global_efficacy(self):
        self._efficacy_spec.validate_efficacy_indicators(
            self._indicators_mapping)
        try:
            self.global_efficacy = (
                self._efficacy_spec.get_global_efficacy_indicator(
                    self._indicators_mapping))

            indicators_specs_map = {
                indicator_spec.name: indicator_spec
                for indicator_spec in self._efficacy_spec.indicators_specs}

            indicators = []
            for indicator_name, value in self._indicators_mapping.items():
                related_indicator_spec = indicators_specs_map[indicator_name]
                indicators.append(
                    Indicator(
                        name=related_indicator_spec.name,
                        description=related_indicator_spec.description,
                        unit=related_indicator_spec.unit,
                        value=value))

            self.indicators = indicators
        except Exception as exc:
            LOG.exception(exc)
            raise exception.GlobalEfficacyComputationError(
                goal=self.goal.name,
                strategy=self.strategy.name)
