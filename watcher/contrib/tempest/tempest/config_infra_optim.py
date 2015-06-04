# Copyright 2014 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function

from oslo_config import cfg

from tempest import config  # noqa

service_available_group = cfg.OptGroup(name="service_available",
                                       title="Available OpenStack Services")

ServiceAvailableGroup = [
    cfg.BoolOpt("watcher",
                default=True,
                help="Whether or not watcher is expected to be available"),
]


class TempestConfigProxyWatcher(object):
    """Wrapper over standard Tempest config that sets Watcher opts."""

    def __init__(self):
        self._config = config.CONF
        config.register_opt_group(
            cfg.CONF, service_available_group, ServiceAvailableGroup)
        self._config.share = cfg.CONF.share

    def __getattr__(self, attr):
        return getattr(self._config, attr)


CONF = TempestConfigProxyWatcher()
