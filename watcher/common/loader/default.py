# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from __future__ import unicode_literals

from oslo_log import log
from stevedore.driver import DriverManager
from stevedore import ExtensionManager

from watcher.common import exception
from watcher.common.loader.base import BaseLoader

LOG = log.getLogger(__name__)


class DefaultLoader(BaseLoader):
    def __init__(self, namespace):
        super(DefaultLoader, self).__init__()
        self.namespace = namespace

    def load(self, name, **kwargs):
        try:
            LOG.debug("Loading in namespace %s => %s ", self.namespace, name)
            driver_manager = DriverManager(namespace=self.namespace,
                                           name=name)
            loaded = driver_manager.driver
        except Exception as exc:
            LOG.exception(exc)
            raise exception.LoadingError(name=name)

        return loaded(**kwargs)

    def list_available(self):
        extension_manager = ExtensionManager(namespace=self.namespace)
        return {ext.name: ext.plugin for ext in extension_manager.extensions}
