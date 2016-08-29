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
class ScoringEngine(loadable.Loadable):
    """A base class for all the Scoring Engines.

    A Scoring Engine is an instance of a data model, to which the learning
    data was applied.

    Please note that this class contains non-static and non-class methods by
    design, so that it's easy to create multiple Scoring Engine instances
    using a single class (possibly configured differently).
    """

    @abc.abstractmethod
    def get_name(self):
        """Returns the name of the Scoring Engine.

        The name should be unique across all Scoring Engines.

        :return: A Scoring Engine name
        :rtype: str
        """

    @abc.abstractmethod
    def get_description(self):
        """Returns the description of the Scoring Engine.

        The description might contain any human readable information, which
        might be useful for Strategy developers planning to use this Scoring
        Engine. It will be also visible in the Watcher API and CLI.

        :return: A Scoring Engine description
        :rtype: str
        """

    @abc.abstractmethod
    def get_metainfo(self):
        """Returns the metadata information about Scoring Engine.

        The metadata might contain a machine-friendly (e.g. in JSON format)
        information needed to use this Scoring Engine. For example, some
        Scoring Engines require to pass the array of features in particular
        order to be able to calculate the score value. This order can be
        defined in metadata and used in Strategy.

        :return: A Scoring Engine metadata
        :rtype: str
        """

    @abc.abstractmethod
    def calculate_score(self, features):
        """Calculates a score value based on arguments passed.

        Scoring Engines might be very different to each other. They might
        solve different problems or use different algorithms or frameworks
        internally. To enable this kind of flexibility, the method takes only
        one argument (string) and produces the results in the same format
        (string). The consumer of the Scoring Engine is ultimately responsible
        for providing the right arguments and parsing the result.

        :param features: Input data for Scoring Engine
        :type features: str
        :return: A score result
        :rtype: str
        """

    @classmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        return []


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
