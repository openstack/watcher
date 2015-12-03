# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

from oslo_config import cfg
from oslo_log import log

from watcher.applier.primitive.wrapper.nova_wrapper import NovaWrapper
from watcher.common.keystone import KeystoneClient
from watcher.metrics_engine.cluster_model_collector.nova import \
    NovaClusterModelCollector

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class CollectorManager(object):
    def get_cluster_model_collector(self):
        keystone = KeystoneClient()
        wrapper = NovaWrapper(keystone.get_credentials(),
                              session=keystone.get_session())
        return NovaClusterModelCollector(wrapper=wrapper)
