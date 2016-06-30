# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc

import six

from watcher.common import service


@six.add_metaclass(abc.ABCMeta)
class Loadable(object):
    """Generic interface for dynamically loading a driver/entry point.

    This defines the contract in order to let the loader manager inject
    the configuration parameters during the loading.
    """

    def __init__(self, config):
        super(Loadable, self).__init__()
        self.config = config

    @classmethod
    @abc.abstractmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        raise NotImplementedError


LoadableSingletonMeta = type(
    "LoadableSingletonMeta", (abc.ABCMeta, service.Singleton), {})


@six.add_metaclass(LoadableSingletonMeta)
class LoadableSingleton(object):
    """Generic interface for dynamically loading a driver as a singleton.

    This defines the contract in order to let the loader manager inject
    the configuration parameters during the loading. Classes inheriting from
    this class will be singletons.
    """

    def __init__(self, config):
        super(LoadableSingleton, self).__init__()
        self.config = config

    @classmethod
    @abc.abstractmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """
        raise NotImplementedError
