# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#          Vincent FRANCOISE <vincent.francoise@b-com.com>
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

from watcher.common import utils
from watcher.decision_engine.loading import default


class CollectorManager(object):

    def __init__(self):
        self.collector_loader = default.ClusterDataModelCollectorLoader()
        self._collectors = None
        self._notification_endpoints = None

    def get_collectors(self):
        if self._collectors is None:
            collectors = utils.Struct()
            collector_plugins = cfg.CONF.collector.collector_plugins
            for collector_name in collector_plugins:
                collector = self.collector_loader.load(collector_name)
                collectors[collector_name] = collector
            self._collectors = collectors

        return self._collectors

    def get_notification_endpoints(self):
        if self._notification_endpoints is None:
            endpoints = []
            for collector in self.get_collectors().values():
                endpoints.extend(collector.notification_endpoints)
            self._notification_endpoints = endpoints

        return self._notification_endpoints

    def get_cluster_model_collector(self, name, osc=None):
        """Retrieve cluster data model collector

        :param name: name of the cluster data model collector plugin
        :type name: str
        :param osc: an OpenStackClients instance
        :type osc: :py:class:`~.OpenStackClients` instance
        :returns: cluster data model collector plugin
        :rtype: :py:class:`~.BaseClusterDataModelCollector`
        """
        return self.collector_loader.load(
            name, osc=osc)
