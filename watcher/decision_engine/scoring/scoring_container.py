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

import abc
import six

from watcher.common.loader import loadable


@six.add_metaclass(abc.ABCMeta)
class ScoringEngineContainer(loadable.Loadable):
    """A base class for all the Scoring Engines Containers.

    A Scoring Engine Container is an abstraction which allows to plugin
    multiple Scoring Engines as a single Stevedore plugin. This enables some
    more advanced scenarios like dynamic reloading of Scoring Engine
    implementations without having to restart any Watcher services.
    """

    @classmethod
    @abc.abstractmethod
    def get_scoring_engine_list(self):
        """Returns a list of Scoring Engine instances.

        :return: A list of Scoring Engine instances
        :rtype: :class: `~.scoring_engine.ScoringEngine`
        """

    @classmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        return []
