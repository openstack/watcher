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

"""
An efficacy specification is a contract that is associated to each :ref:`Goal
<goal_definition>` that defines the various :ref:`efficacy indicators
<efficacy_indicator_definition>` a strategy achieving the associated goal
should provide within its :ref:`solution <solution_definition>`. Indeed, each
solution proposed by a strategy will be validated against this contract before
calculating its :ref:`global efficacy <efficacy_definition>`.
"""

import abc
import jsonschema
from oslo_serialization import jsonutils


class EfficacySpecification(object, metaclass=abc.ABCMeta):

    def __init__(self):
        self._indicators_specs = self.get_indicators_specifications()

    @property
    def indicators_specs(self):
        return self._indicators_specs

    @abc.abstractmethod
    def get_indicators_specifications(self):
        """List the specifications of the indicator for this efficacy spec

        :return: Tuple of indicator specifications
        :rtype: Tuple of :py:class:`~.IndicatorSpecification` instances
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_global_efficacy_indicator(self, indicators_map):
        """Compute the global efficacy for the goal it achieves

        :param indicators_map: dict-like object containing the
                               efficacy indicators related to this spec
        :type indicators_map: :py:class:`~.IndicatorsMap` instance
        :raises: NotImplementedError
        :returns: :py:class:`~.Indicator` instance list, each instance specify
                  global efficacy for different openstack resource.
        """
        raise NotImplementedError()

    @property
    def schema(self):
        """Combined schema from the schema of the indicators"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        for indicator in self.indicators_specs:
            schema["properties"][indicator.name] = indicator.schema
            if indicator.required:
                schema["required"].append(indicator.name)
        return schema

    def validate_efficacy_indicators(self, indicators_map):
        if indicators_map:
            jsonschema.validate(indicators_map, self.schema)
        else:
            True

    def get_indicators_specs_dicts(self):
        return [indicator.to_dict()
                for indicator in self.indicators_specs]

    def serialize_indicators_specs(self):
        return jsonutils.dumps(self.get_indicators_specs_dicts())
