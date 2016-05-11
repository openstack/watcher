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

import socket
import threading

import eventlet
from oslo_config import cfg
from oslo_log import log
import oslo_messaging as om

from watcher.common import rpc
from watcher._i18n import _LE, _LW

# NOTE:
# Ubuntu 14.04 forces librabbitmq when kombu is used
# Unfortunately it forces a version that has a crash
# bug.  Calling eventlet.monkey_patch() tells kombu
# to use libamqp instead.
eventlet.monkey_patch()

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class MessagingHandler(threading.Thread):

    def __init__(self, publisher_id, topic_name, endpoints, version,
                 serializer=None):
        super(MessagingHandler, self).__init__()
        self.publisher_id = publisher_id
        self.topic_name = topic_name
        self.__endpoints = []
        self.__serializer = serializer
        self.__version = version

        self.__server = None
        self.__notifier = None
        self.__transport = None
        self.add_endpoints(endpoints)

    def add_endpoints(self, endpoints):
        self.__endpoints.extend(endpoints)

    def remove_endpoint(self, endpoint):
        if endpoint in self.__endpoints:
            self.__endpoints.remove(endpoint)

    @property
    def endpoints(self):
        return self.__endpoints

    @property
    def transport(self):
        return self.__transport

    def build_notifier(self):
        serializer = rpc.RequestContextSerializer(rpc.JsonPayloadSerializer())
        return om.Notifier(
            self.__transport,
            publisher_id=self.publisher_id,
            topic=self.topic_name,
            serializer=serializer
        )

    def build_server(self, target):
        return om.get_rpc_server(self.__transport, target,
                                 self.__endpoints,
                                 serializer=self.__serializer)

    def _configure(self):
        try:
            self.__transport = om.get_transport(CONF)
            self.__notifier = self.build_notifier()
            if len(self.__endpoints):
                target = om.Target(
                    topic=self.topic_name,
                    # For compatibility, we can override it with 'host' opt
                    server=CONF.host or socket.getfqdn(),
                    version=self.__version,
                )
                self.__server = self.build_server(target)
            else:
                LOG.warning(
                    _LW("No endpoint defined; can only publish events"))
        except Exception as e:
            LOG.exception(e)
            LOG.error(_LE("Messaging configuration error"))

    def run(self):
        LOG.debug("configure MessagingHandler for %s" % self.topic_name)
        self._configure()
        if len(self.__endpoints) > 0:
            LOG.debug("Starting up server")
            self.__server.start()

    def stop(self):
        LOG.debug('Stopped server')
        self.__server.wait()
        self.__server.stop()

    def publish_event(self, event_type, payload, request_id=None):
        self.__notifier.info(
            {'version_api': self.__version,
             'request_id': request_id},
            {'event_id': event_type}, payload
        )
