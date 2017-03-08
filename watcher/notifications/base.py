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

from oslo_config import cfg
from oslo_log import log

from watcher.common import exception
from watcher.common import rpc
from watcher.objects import base
from watcher.objects import fields as wfields

CONF = cfg.CONF
LOG = log.getLogger(__name__)

# Definition of notification levels in increasing order of severity
NOTIFY_LEVELS = {
    wfields.NotificationPriority.DEBUG: 0,
    wfields.NotificationPriority.INFO: 1,
    wfields.NotificationPriority.WARNING: 2,
    wfields.NotificationPriority.ERROR: 3,
    wfields.NotificationPriority.CRITICAL: 4
}


@base.WatcherObjectRegistry.register_if(False)
class NotificationObject(base.WatcherObject):
    """Base class for every notification related versioned object."""

    # Version 1.0: Initial version
    VERSION = '1.0'

    def __init__(self, **kwargs):
        super(NotificationObject, self).__init__(**kwargs)
        # The notification objects are created on the fly when watcher emits
        # the notification. This causes that every object shows every field as
        # changed. We don't want to send this meaningless information so we
        # reset the object after creation.
        self.obj_reset_changes(recursive=False)

    def save(self, context):
        raise exception.UnsupportedError()

    def obj_load_attr(self, attrname):
        raise exception.UnsupportedError()


@base.WatcherObjectRegistry.register_notification
class EventType(NotificationObject):

    # Version 1.0: Initial version
    # Version 1.1: Added STRATEGY action in NotificationAction enum
    # Version 1.2: Added PLANNER action in NotificationAction enum
    # Version 1.3: Added EXECUTION action in NotificationAction enum
    VERSION = '1.3'

    fields = {
        'object': wfields.StringField(),
        'action': wfields.NotificationActionField(),
        'phase': wfields.NotificationPhaseField(nullable=True),
    }

    def to_notification_event_type_field(self):
        """Serialize the object to the wire format."""
        s = '%s.%s' % (self.object, self.action)
        if self.obj_attr_is_set('phase'):
            s += '.%s' % self.phase
        return s


@base.WatcherObjectRegistry.register_if(False)
class NotificationPayloadBase(NotificationObject):
    """Base class for the payload of versioned notifications."""
    # SCHEMA defines how to populate the payload fields. It is a dictionary
    # where every key value pair has the following format:
    # <payload_field_name>: (<data_source_name>,
    #                        <field_of_the_data_source>)
    # The <payload_field_name> is the name where the data will be stored in the
    # payload object, this field has to be defined as a field of the payload.
    # The <data_source_name> shall refer to name of the parameter passed as
    # kwarg to the payload's populate_schema() call and this object will be
    # used as the source of the data. The <field_of_the_data_source> shall be
    # a valid field of the passed argument.
    # The SCHEMA needs to be applied with the populate_schema() call before the
    # notification can be emitted.
    # The value of the payload.<payload_field_name> field will be set by the
    # <data_source_name>.<field_of_the_data_source> field. The
    # <data_source_name> will not be part of the payload object internal or
    # external representation.
    # Payload fields that are not set by the SCHEMA can be filled in the same
    # way as in any versioned object.
    SCHEMA = {}
    # Version 1.0: Initial version
    VERSION = '1.0'

    def __init__(self, **kwargs):
        super(NotificationPayloadBase, self).__init__(**kwargs)
        self.populated = not self.SCHEMA

    def populate_schema(self, **kwargs):
        """Populate the object based on the SCHEMA and the source objects

        :param kwargs: A dict contains the source object at the key defined in
                       the SCHEMA
        """
        for key, (obj, field) in self.SCHEMA.items():
            source = kwargs[obj]
            if source.obj_attr_is_set(field):
                setattr(self, key, getattr(source, field))
        self.populated = True

        # the schema population will create changed fields but we don't need
        # this information in the notification
        self.obj_reset_changes(recursive=False)


@base.WatcherObjectRegistry.register_notification
class NotificationPublisher(NotificationObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'host': wfields.StringField(nullable=False),
        'binary': wfields.StringField(nullable=False),
    }


@base.WatcherObjectRegistry.register_if(False)
class NotificationBase(NotificationObject):
    """Base class for versioned notifications.

    Every subclass shall define a 'payload' field.
    """

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'priority': wfields.NotificationPriorityField(),
        'event_type': wfields.ObjectField('EventType'),
        'publisher': wfields.ObjectField('NotificationPublisher'),
    }

    def save(self, context):
        raise exception.UnsupportedError()

    def obj_load_attr(self, attrname):
        raise exception.UnsupportedError()

    def _should_notify(self):
        """Determine whether the notification should be sent.

        A notification is sent when the level of the notification is
        greater than or equal to the level specified in the
        configuration, in the increasing order of DEBUG, INFO, WARNING,
        ERROR, CRITICAL.
        :return: True if notification should be sent, False otherwise.
        """
        if not CONF.notification_level:
            return False
        return (NOTIFY_LEVELS[self.priority] >=
                NOTIFY_LEVELS[CONF.notification_level])

    def _emit(self, context, event_type, publisher_id, payload):
        notifier = rpc.get_notifier(publisher_id)
        notify = getattr(notifier, self.priority)
        LOG.debug("Emitting notification `%s`", event_type)
        notify(context, event_type=event_type, payload=payload)

    def emit(self, context):
        """Send the notification."""
        if not self._should_notify():
            return
        if not self.payload.populated:
            raise exception.NotificationPayloadError(
                class_name=self.__class__.__name__)
        # Note(gibi): notification payload will be a newly populated object
        # therefore every field of it will look changed so this does not carry
        # any extra information so we drop this from the payload.
        self.payload.obj_reset_changes(recursive=False)

        self._emit(
            context,
            event_type=self.event_type.to_notification_event_type_field(),
            publisher_id='%s:%s' % (self.publisher.binary,
                                    self.publisher.host),
            payload=self.payload.obj_to_primitive())


def notification_sample(sample):
    """Provide a notification sample of the decorated notification.

    Class decorator to attach the notification sample information
    to the notification object for documentation generation purposes.

    :param sample: the path of the sample json file relative to the
                   doc/notification_samples/ directory in the watcher
                   repository root.
    """
    def wrap(cls):
        if not getattr(cls, 'samples', None):
            cls.samples = [sample]
        else:
            cls.samples.append(sample)
        return cls
    return wrap
