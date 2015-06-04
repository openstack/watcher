# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

import eventlet
from oslo_config import cfg
import oslo_messaging as om
from threading import Thread
from watcher.common.messaging.utils.transport_url_builder import \
    TransportUrlBuilder
from watcher.common.rpc import JsonPayloadSerializer
from watcher.common.rpc import RequestContextSerializer
from watcher.openstack.common import log

eventlet.monkey_patch()
LOG = log.getLogger(__name__)

CONF = cfg.CONF


class MessagingHandler(Thread):
    def __init__(self, publisher_id, topic_watcher, endpoint, version,
                 serializer=None):
        Thread.__init__(self)
        self.__server = None
        self.__notifier = None
        self.__endpoints = []
        self.__topics = []
        self._publisher_id = publisher_id
        self._topic_watcher = topic_watcher
        self.__endpoints.append(endpoint)
        self.__version = version
        self.__serializer = serializer

    def add_endpoint(self, endpoint):
        self.__endpoints.append(endpoint)

    def remove_endpoint(self, endpoint):
        if endpoint in self.__endpoints:
            self.__endpoints.remove(endpoint)

    def build_notifier(self):
        serializer = RequestContextSerializer(JsonPayloadSerializer())
        return om.Notifier(
            self.transport,
            driver=CONF.watcher_messaging.notifier_driver,
            publisher_id=self._publisher_id,
            topic=self._topic_watcher,
            serializer=serializer)

    def build_server(self, targets):

        return om.get_rpc_server(self.transport, targets,
                                 self.__endpoints,
                                 executor=CONF.
                                 watcher_messaging.executor,
                                 serializer=self.__serializer)

    def __build_transport_url(self):
        return TransportUrlBuilder().url

    def __config(self):
        try:
            self.transport = om.get_transport(
                cfg.CONF,
                url=self.__build_transport_url())
            self.__notifier = self.build_notifier()
            if 0 < len(self.__endpoints):
                targets = om.Target(
                    topic=self._topic_watcher,
                    server=CONF.watcher_messaging.host,
                    version=self.__version)
                self.__server = self.build_server(targets)
            else:
                LOG.warn("you have no defined endpoint, \
                so you can only publish events")
        except Exception as e:
            LOG.error("configure : %s" % str(e.message))

    def run(self):
        LOG.debug("configure MessagingHandler for %s" % self._topic_watcher)
        self.__config()
        if len(self.__endpoints) > 0:
            LOG.debug("Starting up server")
            self.__server.start()

    def stop(self):
        LOG.debug('Stop up server')
        self.__server.wait()
        self.__server.stop()

    def publish_event(self, event_type, payload, request_id=None):
        self.__notifier.info({'version_api': self.__version,
                              'request_id': request_id},
                             {'event_id': event_type}, payload)
