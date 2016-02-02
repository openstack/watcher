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

from oslo_config import cfg
from oslo_log import log
import oslo_messaging as om

from watcher.common.messaging.events import event_dispatcher as dispatcher
from watcher.common.messaging import messaging_handler
from watcher.common import rpc

from watcher.objects import base

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class MessagingCore(dispatcher.EventDispatcher):

    API_VERSION = '1.0'

    def __init__(self, publisher_id, conductor_topic, status_topic,
                 api_version=API_VERSION):
        super(MessagingCore, self).__init__()
        self.serializer = rpc.RequestContextSerializer(
            base.WatcherObjectSerializer())
        self.publisher_id = publisher_id
        self.api_version = api_version

        self.conductor_topic = conductor_topic
        self.status_topic = status_topic
        self.conductor_topic_handler = self.build_topic_handler(
            conductor_topic)
        self.status_topic_handler = self.build_topic_handler(status_topic)

        self._conductor_client = None
        self._status_client = None

    @property
    def conductor_client(self):
        if self._conductor_client is None:
            transport = om.get_transport(CONF)
            target = om.Target(
                topic=self.conductor_topic,
                version=self.API_VERSION,
            )
            self._conductor_client = om.RPCClient(
                transport, target, serializer=self.serializer)
        return self._conductor_client

    @conductor_client.setter
    def conductor_client(self, c):
        self.conductor_client = c

    @property
    def status_client(self):
        if self._status_client is None:
            transport = om.get_transport(CONF)
            target = om.Target(
                topic=self.status_topic,
                version=self.API_VERSION,
            )
            self._status_client = om.RPCClient(
                transport, target, serializer=self.serializer)
        return self._status_client

    @status_client.setter
    def status_client(self, c):
        self.status_client = c

    def build_topic_handler(self, topic_name):
        return messaging_handler.MessagingHandler(
            self.publisher_id, topic_name, self,
            self.api_version, self.serializer)

    def connect(self):
        LOG.debug("Connecting to '%s' (%s)",
                  CONF.transport_url, CONF.rpc_backend)
        self.conductor_topic_handler.start()
        self.status_topic_handler.start()

    def disconnect(self):
        LOG.debug("Disconnecting from '%s' (%s)",
                  CONF.transport_url, CONF.rpc_backend)
        self.conductor_topic_handler.stop()
        self.status_topic_handler.stop()

    def publish_control(self, event, payload):
        return self.conductor_topic_handler.publish_event(event, payload)

    def publish_status(self, event, payload, request_id=None):
        return self.status_topic_handler.publish_event(
            event, payload, request_id)

    def get_version(self):
        return self.api_version

    def check_api_version(self, context):
        api_manager_version = self.conductor_client.call(
            context.to_dict(), 'check_api_version',
            api_version=self.api_version)
        return api_manager_version

    def response(self, evt, ctx, message):
        payload = {
            'request_id': ctx['request_id'],
            'msg': message
        }
        self.publish_status(evt, payload)
