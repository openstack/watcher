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

from __future__ import unicode_literals

from oslo_config import cfg
from oslo_log import log
from stevedore import driver as drivermanager
from stevedore import extension as extensionmanager

from watcher.common import exception
from watcher.common.loader import base
from watcher.common import utils

LOG = log.getLogger(__name__)


class DefaultLoader(base.BaseLoader):

    def __init__(self, namespace, conf=cfg.CONF):
        """Entry point loader for Watcher using Stevedore

        :param namespace: namespace of the entry point(s) to load or list
        :type namespace: str
        :param conf: ConfigOpts instance, defaults to cfg.CONF
        """
        super(DefaultLoader, self).__init__()
        self.namespace = namespace
        self.conf = conf

    def load(self, name, **kwargs):
        try:
            LOG.debug("Loading in namespace %s => %s ", self.namespace, name)
            driver_manager = drivermanager.DriverManager(
                namespace=self.namespace,
                name=name,
                invoke_on_load=False,
            )

            driver_cls = driver_manager.driver
            config = self._load_plugin_config(name, driver_cls)

            driver = driver_cls(config, **kwargs)
        except Exception as exc:
            LOG.exception(exc)
            raise exception.LoadingError(name=name)

        return driver

    def _reload_config(self):
        self.conf(default_config_files=self.conf.default_config_files)

    def get_entry_name(self, name):
        return ".".join([self.namespace, name])

    def _load_plugin_config(self, name, driver_cls):
        """Load the config of the plugin"""
        config = utils.Struct()
        config_opts = driver_cls.get_config_opts()
        if not config_opts:
            return config

        group_name = self.get_entry_name(name)
        self.conf.register_opts(config_opts, group=group_name)

        # Finalise the opt import by re-checking the configuration
        # against the provided config files
        self._reload_config()

        config_group = self.conf.get(group_name)
        if not config_group:
            raise exception.LoadingError(name=name)

        config.update({
            name: value for name, value in config_group.items()
        })

        return config

    def list_available(self):
        extension_manager = extensionmanager.ExtensionManager(
            namespace=self.namespace)
        return {ext.name: ext.plugin for ext in extension_manager.extensions}
