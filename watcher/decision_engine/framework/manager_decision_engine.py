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
from concurrent.futures import ThreadPoolExecutor

from oslo_config import cfg

from watcher.decision_engine.framework.events.event_consumer_factory import \
    EventConsumerFactory

from watcher.common.messaging.messaging_core import \
    MessagingCore
from watcher.decision_engine.framework.messaging.audit_endpoint import \
    AuditEndpoint
from watcher.decision_engine.framework.messaging.events import Events

from watcher.common.messaging.notification_handler import \
    NotificationHandler
from watcher.decision_engine.framework.strategy.StrategyManagerImpl import \
    StrategyContextImpl
from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF

WATCHER_DECISION_ENGINE_OPTS = [
    cfg.StrOpt('topic_control',
               default='watcher.decision.control',
               help='The topic name used for'
                    'control events, this topic '
                    'used for rpc call '),
    cfg.StrOpt('topic_status',
               default='watcher.decision.status',
               help='The topic name used for '
                    'status events, this topic '
                    'is used so as to notify'
                    'the others components '
                    'of the system'),
    cfg.StrOpt('publisher_id',
               default='watcher.decision.api',
               help='The identifier used by watcher '
                    'module on the message broker')
]
decision_engine_opt_group = cfg.OptGroup(
    name='watcher_decision_engine',
    title='Defines the parameters of the module decision engine')
CONF.register_group(decision_engine_opt_group)
CONF.register_opts(WATCHER_DECISION_ENGINE_OPTS, decision_engine_opt_group)


class DecisionEngineManager(MessagingCore):
    API_VERSION = '1.0'

    def __init__(self):
        MessagingCore.__init__(self, CONF.watcher_decision_engine.publisher_id,
                               CONF.watcher_decision_engine.topic_control,
                               CONF.watcher_decision_engine.topic_status)
        self.handler = NotificationHandler(self.publisher_id)
        self.handler.register_observer(self)
        self.add_event_listener(Events.ALL, self.event_receive)
        # todo(jed) oslo_conf
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.topic_control.add_endpoint(AuditEndpoint(self))
        self.context = StrategyContextImpl(self)

    def join(self):
        self.topic_control.join()
        self.topic_status.join()

    # TODO(ebe): Producer / consumer
    def event_receive(self, event):
        try:
            request_id = event.get_request_id()
            event_type = event.get_type()
            data = event.get_data()
            LOG.debug("request id => %s" % event.get_request_id())
            LOG.debug("type_event => %s" % str(event.get_type()))
            LOG.debug("data       => %s" % str(data))

            event_consumer = EventConsumerFactory().factory(event_type)
            event_consumer.set_messaging(self)
            event_consumer.execute(request_id, data)
        except Exception as e:
            LOG.error("evt %s" % e.message)
            raise e
