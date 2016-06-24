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

from watcher.common import utils
from watcher.metrics_engine.loading import default


CONF = cfg.CONF


class CollectorManager(object):

    def __init__(self):
        self.collector_loader = default.ClusterDataModelCollectorLoader()
        self._collectors = None

    def get_collectors(self):
        if self._collectors is None:
            collectors = utils.Struct()
            available_collectors = self.collector_loader.list_available()
            for collector_name in available_collectors:
                collector = self.collector_loader.load(collector_name)
                collectors[collector_name] = collector
                self._collectors = collectors

        return self._collectors

    def get_cluster_model_collector(self, name, osc=None):
        """Retrieve cluster data model collector

        :param name: name of the cluster data model collector plugin
        :type name: str
        :param osc: an OpenStackClients instance
        :type osc: :py:class:`~.OpenStackClients` instance
        :returns: cluster data model collector plugin
        :rtype: :py:class:`~.BaseClusterDataModelCollector`
        """
        return self.collector_loader.load(name, osc=osc)
