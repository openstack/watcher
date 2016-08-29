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


class FakeStrategy(base_strategy.BaseStrategy):

    NAME = NotImplemented
    DISPLAY_NAME = NotImplemented
    GOAL_NAME = NotImplemented

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
    def get_config_opts(cls):
        return []

    def pre_execute(self):
        pass

    def do_execute(self):
        pass

    def post_execute(self):
        pass


class FakeDummy1Strategy1(FakeStrategy):
    GOAL_NAME = "dummy_1"
    NAME = "strategy_1"
    DISPLAY_NAME = "Strategy 1"

    @classmethod
    def get_config_opts(cls):
        return [
            cfg.StrOpt('test_opt', help="Option used for testing."),
        ]


class FakeDummy1Strategy2(FakeStrategy):
    GOAL_NAME = "dummy_1"
    NAME = "strategy_2"
    DISPLAY_NAME = "Strategy 2"


class FakeDummy2Strategy3(FakeStrategy):
    GOAL_NAME = "dummy_2"
    NAME = "strategy_3"
    DISPLAY_NAME = "Strategy 3"


class FakeDummy2Strategy4(FakeStrategy):
    GOAL_NAME = "dummy_2"
    NAME = "strategy_4"
    DISPLAY_NAME = "Strategy 4"
