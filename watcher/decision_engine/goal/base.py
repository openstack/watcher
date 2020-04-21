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

import abc

from watcher.common.loader import loadable


class Goal(loadable.Loadable, metaclass=abc.ABCMeta):

    def __init__(self, config):
        super(Goal, self).__init__(config)
        self.name = self.get_name()
        self.display_name = self.get_display_name()
        self.efficacy_specification = self.get_efficacy_specification()

    @classmethod
    @abc.abstractmethod
    def get_name(cls):
        """Name of the goal: should be identical to the related entry point"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_display_name(cls):
        """The goal display name for the goal"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_translatable_display_name(cls):
        """The translatable msgid of the goal"""
        # Note(v-francoise): Defined here to be used as the translation key for
        # other services
        raise NotImplementedError()

    @classmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        return []

    @abc.abstractmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        raise NotImplementedError()
