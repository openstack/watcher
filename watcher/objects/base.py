#    Copyright 2013 IBM Corp.
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

"""Watcher common internal object model"""

from oslo_utils import versionutils
from oslo_versionedobjects import base as ovo_base
from oslo_versionedobjects import fields as ovo_fields

from watcher import objects

remotable_classmethod = ovo_base.remotable_classmethod
remotable = ovo_base.remotable


def get_attrname(name):
    """Return the mangled name of the attribute's underlying storage."""
    # FIXME(danms): This is just until we use o.vo's class properties
    # and object base.
    return '_obj_' + name


class WatcherObjectRegistry(ovo_base.VersionedObjectRegistry):
    notification_classes = []

    def registration_hook(self, cls, index):
        # NOTE(danms): This is called when an object is registered,
        # and is responsible for maintaining watcher.objects.$OBJECT
        # as the highest-versioned implementation of a given object.
        version = versionutils.convert_version_to_tuple(cls.VERSION)
        if not hasattr(objects, cls.obj_name()):
            setattr(objects, cls.obj_name(), cls)
        else:
            cur_version = versionutils.convert_version_to_tuple(
                getattr(objects, cls.obj_name()).VERSION)
            if version >= cur_version:
                setattr(objects, cls.obj_name(), cls)

    @classmethod
    def register_notification(cls, notification_cls):
        """Register a class as notification.

        Use only to register concrete notification or payload classes,
        do not register base classes intended for inheritance only.
        """
        cls.register_if(False)(notification_cls)
        cls.notification_classes.append(notification_cls)
        return notification_cls

    @classmethod
    def register_notification_objects(cls):
        """Register previously decorated notification as normal ovos.

        This is not intended for production use but only for testing and
        document generation purposes.
        """
        for notification_cls in cls.notification_classes:
            cls.register(notification_cls)


class WatcherObject(ovo_base.VersionedObject):
    """Base class and object factory.

    This forms the base of all objects that can be remoted or instantiated
    via RPC. Simply defining a class that inherits from this base class
    will make it remotely instantiatable. Objects should implement the
    necessary "get" classmethod routines as well as "save" object methods
    as appropriate.
    """

    OBJ_SERIAL_NAMESPACE = 'watcher_object'
    OBJ_PROJECT_NAMESPACE = 'watcher'

    def as_dict(self):
        return {
            k: getattr(self, k) for k in self.fields
            if self.obj_attr_is_set(k)}


class WatcherObjectDictCompat(ovo_base.VersionedObjectDictCompat):
    pass


class WatcherPersistentObject(object):
    """Mixin class for Persistent objects.

    This adds the fields that we use in common for all persistent objects.
    """
    fields = {
        'created_at': ovo_fields.DateTimeField(nullable=True),
        'updated_at': ovo_fields.DateTimeField(nullable=True),
        'deleted_at': ovo_fields.DateTimeField(nullable=True),
    }

    def obj_refresh(self, loaded_object):
        """Applies updates for objects that inherit from base.WatcherObject.

        Checks for updated attributes in an object. Updates are applied from
        the loaded object column by column in comparison with the current
        object.
        """
        for field in self.fields:
            if (self.obj_attr_is_set(field) and
                    self[field] != loaded_object[field]):
                self[field] = loaded_object[field]

    @staticmethod
    def _from_db_object(obj, db_object):
        """Converts a database entity to a formal object.

        :param obj: An object of the class.
        :param db_object: A DB model of the object
        :return: The object of the class with the database entity added

        """

        for field in obj.fields:
            obj[field] = db_object[field]

        obj.obj_reset_changes()
        return obj


class WatcherObjectSerializer(ovo_base.VersionedObjectSerializer):
    # Base class to use for object hydration
    OBJ_BASE_CLASS = WatcherObject
