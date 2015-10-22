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
import oslo_messaging as om

from watcher.common import exception
from watcher.common import utils


from watcher.common.messaging.messaging_core import MessagingCore
from watcher.common.messaging.notification_handler import NotificationHandler
from watcher.common.messaging.utils.transport_url_builder import \
    TransportUrlBuilder
from watcher.decision_engine.framework.events.event_consumer_factory import \
    EventConsumerFactory
from watcher.decision_engine.framework.manager_decision_engine import \
    decision_engine_opt_group
from watcher.decision_engine.framework.manager_decision_engine import \
    WATCHER_DECISION_ENGINE_OPTS

from watcher.decision_engine.framework.messaging.events import Events

from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF

CONF.register_group(decision_engine_opt_group)
CONF.register_opts(WATCHER_DECISION_ENGINE_OPTS, decision_engine_opt_group)


class DecisionEngineAPI(MessagingCore):
    # This must be in sync with manager.DecisionEngineManager's.
    MessagingCore.API_VERSION = '1.0'

    def __init__(self):
        MessagingCore.__init__(self, CONF.watcher_decision_engine.publisher_id,
                               CONF.watcher_decision_engine.topic_control,
                               CONF.watcher_decision_engine.topic_status)
        self.handler = NotificationHandler(self.publisher_id)
        self.handler.register_observer(self)
        self.add_event_listener(Events.ALL, self.event_receive)
        self.topic_status.add_endpoint(self.handler)

        transport = om.get_transport(CONF, TransportUrlBuilder().url)
        target = om.Target(
            topic=CONF.watcher_decision_engine.topic_control,
            version=MessagingCore.API_VERSION)

        self.client = om.RPCClient(transport, target,
                                   serializer=self.serializer)

    def trigger_audit(self, context, audit_uuid=None):
        if not utils.is_uuid_like(audit_uuid):
            raise exception.InvalidUuidOrName(name=audit_uuid)

        return self.client.call(
            context.to_dict(), 'trigger_audit', audit_uuid=audit_uuid)

    # TODO(ebe): Producteur / consommateur implementer
    def event_receive(self, event):

        try:
            request_id = event.get_request_id()
            event_type = event.get_type()
            data = event.get_data()
            LOG.debug("request id => %s" % event.get_request_id())
            LOG.debug("type_event => %s" % str(event.get_type()))
            LOG.debug("data       => %s" % str(data))

            event_consumer = EventConsumerFactory.factory(event_type)
            event_consumer.execute(request_id, self.context, data)
        except Exception as e:
            LOG.error("evt %s" % e.message)
            raise e
