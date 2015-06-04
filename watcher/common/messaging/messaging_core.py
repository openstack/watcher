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

from watcher.common.messaging.events.event_dispatcher import \
    EventDispatcher
from watcher.common.messaging.messaging_handler import \
    MessagingHandler
from watcher.common.rpc import RequestContextSerializer

from watcher.objects.base import WatcherObjectSerializer
from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF

WATCHER_MESSAGING_OPTS = [
    cfg.StrOpt('notifier_driver',
               default='messaging', help='The name of the driver used by'
                                         ' oslo messaging'),
    cfg.StrOpt('executor',
               default='eventlet', help='The name of a message executor, for'
                                        'example: eventlet, blocking'),
    cfg.StrOpt('protocol',
               default='rabbit', help='The protocol used by the message'
                                      ' broker, for example rabbit'),
    cfg.StrOpt('user',
               default='guest', help='The username used by the message '
                                     'broker'),
    cfg.StrOpt('password',
               default='guest', help='The password of user used by the '
                                     'message broker'),
    cfg.StrOpt('host',
               default='localhost', help='The host where the message broker'
                                         'is installed'),
    cfg.StrOpt('port',
               default='5672', help='The port used bythe message broker'),
    cfg.StrOpt('virtual_host',
               default='', help='The virtual host used by the message '
                                'broker')
]

CONF = cfg.CONF
opt_group = cfg.OptGroup(name='watcher_messaging',
                         title='Options for the messaging core')
CONF.register_group(opt_group)
CONF.register_opts(WATCHER_MESSAGING_OPTS, opt_group)


class MessagingCore(EventDispatcher):
    API_VERSION = '1.0'

    def __init__(self, publisher_id, topic_control, topic_status):
        EventDispatcher.__init__(self)
        self.serializer = RequestContextSerializer(WatcherObjectSerializer())
        self.publisher_id = publisher_id
        self.topic_control = self.build_topic(topic_control)
        self.topic_status = self.build_topic(topic_status)

    def build_topic(self, topic_name):
        return MessagingHandler(self.publisher_id, topic_name, self,
                                self.API_VERSION, self.serializer)

    def connect(self):
        LOG.debug("connecting to rabbitMQ broker")
        self.topic_control.start()
        self.topic_status.start()

    def disconnect(self):
        LOG.debug("Disconnect to rabbitMQ broker")
        self.topic_control.stop()
        self.topic_status.stop()

    def publish_control(self, event, payload):
        return self.topic_control.publish_event(event, payload)

    def publish_status(self, event, payload, request_id=None):
        return self.topic_status.publish_event(event, payload, request_id)

    def get_version(self):
        return self.API_VERSION

    def check_api_version(self, context):
        api_manager_version = self.client.call(
            context.to_dict(), 'check_api_version',
            api_version=self.API_VERSION)
        return api_manager_version

    def response(self, evt, ctx, message):
        payload = {
            'request_id': ctx['request_id'],
            'msg': message
        }
        self.publish_status(evt, payload)
