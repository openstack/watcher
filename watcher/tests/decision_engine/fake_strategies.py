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

from oslo_config import cfg

from watcher.decision_engine.strategy.strategies import base as base_strategy

CONF = cfg.CONF


class FakeStrategy(base_strategy.BaseStrategy):

    GOAL_NAME = NotImplemented
    GOAL_DISPLAY_NAME = NotImplemented
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
    def get_goal_name(cls):
        return cls.GOAL_NAME

    @classmethod
    def get_goal_display_name(cls):
        return cls.GOAL_DISPLAY_NAME

    @classmethod
    def get_translatable_goal_display_name(cls):
        return cls.GOAL_DISPLAY_NAME

    @classmethod
    def get_config_opts(cls):
        return []

    def execute(self, original_model):
        pass


class FakeDummy1Strategy1(FakeStrategy):
    GOAL_NAME = "DUMMY_1"
    GOAL_DISPLAY_NAME = "Dummy 1"
    NAME = "STRATEGY_1"
    DISPLAY_NAME = "Strategy 1"

    @classmethod
    def get_config_opts(cls):
        return [
            cfg.StrOpt('test_opt', help="Option used for testing."),
        ]


class FakeDummy1Strategy2(FakeStrategy):
    GOAL_NAME = "DUMMY_1"
    GOAL_DISPLAY_NAME = "Dummy 1"
    NAME = "STRATEGY_2"
    DISPLAY_NAME = "Strategy 2"


class FakeDummy2Strategy3(FakeStrategy):
    GOAL_NAME = "DUMMY_2"
    GOAL_DISPLAY_NAME = "Dummy 2"
    NAME = "STRATEGY_3"
    DISPLAY_NAME = "Strategy 3"


class FakeDummy2Strategy4(FakeStrategy):
    GOAL_NAME = "DUMMY_2"
    GOAL_DISPLAY_NAME = "Other Dummy 2"
    NAME = "STRATEGY_4"
    DISPLAY_NAME = "Strategy 4"
