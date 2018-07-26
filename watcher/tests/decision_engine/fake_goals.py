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

from watcher.decision_engine.goal import base as base_goal
from watcher.decision_engine.goal.efficacy import base as efficacy_base
from watcher.decision_engine.goal.efficacy import indicators
from watcher.decision_engine.goal.efficacy import specs


class FakeGoal(base_goal.Goal):

    NAME = NotImplemented
    DISPLAY_NAME = NotImplemented

    @classmethod
    def get_name(cls):
        return cls.NAME

    @classmethod
    def get_display_name(cls):
        return cls.DISPLAY_NAME

    @classmethod
    def get_translatable_display_name(cls):
        return cls.DISPLAY_NAME

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()


class DummyIndicator(indicators.IndicatorSpecification):
    def __init__(self):
        super(DummyIndicator, self).__init__(
            name="dummy",
            description="Dummy indicator",
            unit="%",
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
            }


class DummySpec1(efficacy_base.EfficacySpecification):

    def get_indicators_specifications(self):
        return [DummyIndicator()]

    def get_global_efficacy_indicator(self, indicators_map):
        return None


class FakeDummy1(FakeGoal):
    NAME = "dummy_1"
    DISPLAY_NAME = "Dummy 1"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return DummySpec1()


class FakeDummy2(FakeGoal):
    NAME = "dummy_2"
    DISPLAY_NAME = "Dummy 2"
